"""
Bluetooth manager - Handles Bluetooth connections using Bleak library
"""

#Add bleak library
import asyncio
from bleak import BleakScanner, BleakClient
from PyQt6.QtCore import QObject, pyqtSignal, QThread

"""
Manages bluetooth connections
Scanning, connecting, sending/receiving data
"""
class BluetoothManager(QObject):

    #Define signals
    scan_started = pyqtSignal()
    device_found = pyqtSignal(str, str)     #name and address
    scan_complete = pyqtSignal(list)        #list of devices
    connected = pyqtSignal(str)             #device name
    disconnected = pyqtSignal()
    data_received = pyqtSignal(bytes)       #data
    error_occurred = pyqtSignal(str)         #sends error message

    def __init__(self):
        super().__init__()

        #Connection state
        self.client = None
        self.connected_device = None
        self.is_connected = False

        #Characteristic UUIDs
        self.notify_characteristic_uuid = None  #UUID for receiving data
        self.write_characteristic_uuid = None  #UUID for sending data
    
    #Scan for devices
    #Returns list of devices(name, address)
    async def scan_devices(self, timeout = 10.0):
        #Try scanning, error when nothing found
        try:
            self.scan_started.emit()    #scanning began
            devices = await BleakScanner.discover(timeout=timeout)  #returns device objects after 10 s
            found_devices = []

            #Loop through each device found
            for device in devices:
                #Assign name if exists
                name = device.name if device.name else "Unknown"
                #MAC address
                address = device.address

                self.device_found.emit(name, address)   #signal device found
                found_devices.append((name, address))   #add device to list
            
            #Scanning complete
            self.scan_complete.emit(found_devices)
            return found_devices

        except Exception as e:
            error_msg = f"Scan error: {str(e)}"
            self.error_occurred.emit(error_msg)  #error signal
            return []                           #return empty list
    
    #Connect to device by MAC address
    async def connect_to_device(self, address):
        
        try:
            #BleakClient object, manages connection
            #calls function on disconnect
            self.client = BleakClient(address,
                                      disconnected_callback=self._on_disconnect)
            
            #Connect
            await self.client.connect()

            #Check if connect
            if self.client.is_connected:
                self.is_connected = True
                self.connected_device = address     #device connected to
                device_name = address               #use address as name

                await self._discover_uuids()        #discover uuids

                self.connected.emit(device_name)    #signal device connected

                #start listening for data
                if self.notify_characteristic_uuid:
                    await self._start_notifications()
                
                return True #successful
            else:
                raise Exception("Connection Failed.")
            
        except  Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.error_occurred.emit(error_msg)  #error signal
            return False                        #failed
    
    #Automatically discover UUIDs for notify and write characteristics
    async def _discover_uuids(self):
        try:
            #Run through services
            services = self.client.services

            #Loop through services and characteristics
            for service in services:
                
                for char in service.characteristics:
                   
                    #if has notify and we do not have
                    if "notify" in char.properties and not self.notify_characteristic_uuid:
                        self.notify_characteristic_uuid = char.uuid
                        

                    #if has write and we do not have
                    if ("write" in char.properties or "write-without-response" in char.properties) and not self.write_characteristic_uuid:
                        self.write_characteristic_uuid = char.uuid   

            print(f"\nFinal NOTIFY UUID: {self.notify_characteristic_uuid}")
            print(f"Final WRITE UUID: {self.write_characteristic_uuid}")
            print("=== End Discovery ===\n")            
        except Exception as e:
            error_msg = f"UUID discovery error: {str(e)}"
            self.error_occurred.emit(error_msg)
          
    #Disconnect from device
    async def disconnect(self):
        try:
            if self.client and self.is_connected:
                await self.client.disconnect()

                #update
                self.is_connected = False
                self.connected_device = None
                self.notify_characteristic_uuid = None
                self.write_characteristic_uuid = None
        except Exception as e:
            #still update if fails
            self.is_connected = False
            self.connected_device = None
    
    #Send data to connected device
    async def send_data(self, data):
        try:
            #check if connected
            if not self.is_connected or not self.client:
                raise Exception("Not connected to a device")
            #check for write UUID
            if not self.write_characteristic_uuid:
                raise Exception("Write characteristic UUID not set")
            
            #convert to bytes
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            #send data to uuiid
            await self.client.write_gatt_char(
                self.write_characteristic_uuid,
                data
            )

        except Exception as e:
            error_msg = f"Error sending: {str(e)}"
            self.error_occurred.emit(error_msg)  #error signal
    
    #_for internal
    #start listening for notifications, tells device to send data
    async def _start_notifications(self):
        try:
            #start listening, then call notification handler
            await self.client.start_notify(
                self.notify_characteristic_uuid,    #uuid to listen to
                self._notification_handler          #call when data comes in
            )
        except Exception as e:
            error_msg = f"Notification error: {str(e)}"
            self.error_occurred.emit(error_msg)  #error signal
    
    #handles notifications
    def _notification_handler(self, sender, data):
        if isinstance(data, bytearray):
            data = bytes(data)
        self.data_received.emit(data)
    
    #called when device disconnects
    def _on_disconnect(self, client):
        self.is_connected = False
        self.client = None
        self.disconnected.emit()
    
    #set receiving uuid
    def set_notify_characteristic(self, uuid):
        self.notify_characteristic_uuid = uuid
    #set writing uuid
    def set_write_characteristic(self, uuid):
        self.write_characteristic_uuid = uuid

#Worker thread
#Runs Bluetooth in separate thread from GUI
class BluetoothWorker(QThread):
    #Define signals
    scan_complete = pyqtSignal(list)    #when scan is complete
    connected = pyqtSignal(bool)        #when scan succeeds/fails
    disconnected = pyqtSignal()         #when device disconnects
    error = pyqtSignal(str)             #when error occurs
    reconnecting = pyqtSignal(int)      #attempt number when reconnecting

    def __init__(self):
        super().__init__()

        #create manager
        self.manager = BluetoothManager()

        #will tell operation
        self.operation = None  
        self.params = {}

        #store event loop
        self.loop = None

        #connects manager signals to worker signals
        self.manager.scan_complete.connect(self.scan_complete.emit)

        #ignore name, send connected signal
        self.manager.connected.connect(lambda name: self.connected.emit(True))

        #disconnect
        self.manager.disconnected.connect(self.disconnected.emit)
        #error
        self.manager.error_occurred.connect(self.error.emit)

        self.running = False    #track worker if reconnect needed

        #Auto reconnect settings
        self.connection_timeout = 5.0
        self.auto_reconnect = False
        self.reconnect_attempts = 2
        self.reconnect_delay = 1.0
        self.last_connected_address = None

    #Runs in background
    def run(self):
            
        try:
            #Event loop
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            #check operation
            if self.operation == "scan":
                #run scan operation
                self.loop.run_until_complete(
                    self.manager.scan_devices(self.params.get('timeout', 10.0)) #gets timeout, defaults 10 s
                )
                self.loop.close()    #close loop after scan
            elif self.operation == "connect":
                address = self.params.get('address')
                self.last_connected_address = address   #store address for reconnect
                #run connect operation
                successful = self.loop.run_until_complete(
                    self.manager.connect_to_device(self.params.get('address'))
                )
                if successful:
                    self.running = True    #program running
                    self.loop.run_forever() #keep loop running once connected

                    #if auto reconnect is enabled, attempt reconnect
                    if self.running and self.auto_reconnect:
                        self.loop.run_until_complete(self.attempt_reconnect())

                self.loop.close()
                
        except Exception as e:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            self.error.emit(f"Error in Bluetooth worker: {str(e)}")

    #Run coroutine for disconnecting and sending
    def _run_in_loop(self, coroutine):
        if self.loop and self.loop.is_running():
            future_loop = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
            try:
                return future_loop.result(timeout=10.0) #wait for result
            except Exception as e:
                self.error.emit(f"Error within operation: {str(e)}")
                return None
        else:
            self.error.emit("Event loop not running")
            return None

    #scan for devices
    def scan(self, timeout=10.0):
        if self.isRunning():
            self.error.emit("Already running")
            return
        self.operation = "scan"                 #tell run() to scan
        self.params = {'timeout': timeout}      #store timeout
        self.start()
        
    #connect to a device
    def connect(self, address):
        if self.isRunning():
            self.error.emit("Already running")
            return
        self.operation = "connect"                 #tell run() to connect
        self.params = {'address': address}         #store timeout
        self.start()
        
    #planned disconnect from device
    def disconnect_device(self):
        #disconnect and stop event loop
        if self.loop and self.loop.is_running():
            self.running = False
            self.auto_reconnect = False
            self.last_connected_address = None  #clear stored address
            self._run_in_loop(self.manager.disconnect())
            self.loop.call_soon_threadsafe(self.loop.stop)
            

    #send data to device
    def send(self, data):
        #send using event loop
        self._run_in_loop(self.manager.send_data(data))

    #Set connection timeout
    def set_connection_timeout(self, timeout):
        self.connection_timeout = timeout
    
    #Set auto reconnect enable/disable
    def set_auto_reconnect_enable(self, enabled):
        self.auto_reconnect = enabled
    
    #Set auto reconnect attempts
    def set_reconnect_attempts(self, attempts):
        self.reconnect_attempts = attempts
    
    #Set delay between attempts
    def set_reconnect_delay(self, delay):
        self.reconnect_delay = delay

    #Attempt reconnect
    async def attempt_reconnect(self):
        address = self.last_connected_address
        #if not stored, cannot reconnect
        if not address:
            self.error.emit("No connected device to reconnect to")
            return False
        
        #try reconnect
        if self.running and self.auto_reconnect:
            try:
                for attempt in range(1, self.reconnect_attempts + 1):
                    self.reconnecting.emit(attempt)
                    if attempt > 1:
                        await asyncio.sleep(self.reconnect_delay)
                    #Retry connection
                    successful = await self.manager.connect_to_device(address)
                    if successful:
                        self.running = True
                        self.loop.run_forever()
                        return True

            except Exception as e:
                #if all attempts failed, emit error
                self.running = False    #stop program
                self.error.emit(f"Reconnect failed after {self.reconnect_attempts} attempts")
                self.disconnected.emit()    #signal device disconnected
                return False    #failed