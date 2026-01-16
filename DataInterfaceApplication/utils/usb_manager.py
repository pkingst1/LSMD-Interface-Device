"""
USB Manager - Handles USB connections using pyserial library
"""

#Add serial library
import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, pyqtSignal, QThread

"""
Manages USB connections
Scanning, connecting, sending/recieving data
"""
class USBManager(QObject):
    #Define signals
    scan_started = pyqtSignal()
    device_found = pyqtSignal(str, str)     #name and address port
    scan_complete = pyqtSignal(list)        #list of devices    
    connected = pyqtSignal(str)             #device name
    disconnected = pyqtSignal()             
    data_received = pyqtSignal(bytes)       #data
    error_occurred = pyqtSignal(str)         #sends error message

    def __init__(self):
        super().__init__()

        #Connection state
        self.serial_port = None
        self.connected_device = None
        self.is_connected = False

        #Serial settings
        self.baud_rate = 230400  #default, must match PIC rate
        self.timeout = 1

    #Scan for USB devices
    #Returns list of devices(description, port name)
    def scan_devices(self):
        try:
            self.scan_started.emit()    #scanning began
            ports = serial.tools.list_ports.comports()  #get ports
            found_ports = []

            #Loop through found ports
            for port in ports:
                #Description
                name = port.description if port.description else "Unknown"
                #Name
                port_name = port.device

                self.device_found.emit(name, port_name)   #signal device found
                found_ports.append((name, port_name))     #add port to list
            
            #Scan complete
            self.scan_complete.emit(found_ports)
            return found_ports    #return list of devices

        except Exception as e:
            error_msg = f"Scan error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return  []       #return empty list if error

    #Connect to port
    def connect(self, port_name):
        try:
            #Serial connection
            self.serial_port = serial.Serial(port = port_name, baudrate = self.baud_rate, timeout=self.timeout)
            #Check for connection
            if self.serial_port.is_open:
                self.is_connected = True
                self.connected_device = port_name
                self.connected.emit(port_name)    #signal device connected
                return True                       #successful
            else:
                raise Exception("Failed to connect to port")

        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False                        #failed

    #Disconnect from port
    def disconnect(self):
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()    #Update state of connection
                self.is_connected = False
                self.connected_device = None
                self.disconnected.emit()
                return True

            else:
                raise Exception("Not connected to a port")

        except Exception as e:
            #Update if fails
            self.is_connected = False
            self.connected_device = None

            error_msg = f"Disconnection error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False    #failed to disconnect         
    
    #Send data to port
    def send_data(self, data):
        try:
            #Check for connection
            if not self.is_connected or not self.serial_port:
                raise Exception("Not connected to a port")
            
            #convert to bytes
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            #send data
            self.serial_port.write(data)
            return True    #success
        
        except Exception as e:
            error_msg = f"Error sending: {str(e)}"
            self.error_occurred.emit(error_msg)
            return False
    
    def read_data(self):
        try:
            #Check if connected and if data available
            if self.serial_port and self.serial_port.is_open:
                data = self.serial_port.read(self.serial_port.in_waiting)
                if data:
                    self.data_received.emit(data)
                    return data    #data received
                else:
                    return None    #no data available
            else:
                raise Exception("Not connected to a port")
        
        except Exception as e:
            error_msg = f"Error reading: {str(e)}"
            self.error_occurred.emit(error_msg)
            return None    #failed to read
    
    #Set baud rate
    def set_baud_rate(self, baud_rate):
        self.baud_rate = baud_rate
    
    #Set timeout
    def set_timeout(self, timeout):
        self.timeout = timeout
    
    #Get baud rate
    def get_baud_rate(self):
        return self.baud_rate
    
    #Get timeout
    def get_timeout(self):
        return self.timeout
    
    #Get connected device
    def get_connected_device(self):
        return self.connected_device
    
    #Get connection state
    def get_connection_state(self):
        return self.is_connected
    
    #Get serial port
    def get_serial_port(self):
        return self.serial_port

#Worker thread
#Runs USB in separate thread from GUI
class USBWorker(QThread):
    #Define signals
    scan_complete = pyqtSignal(list)    #when scan is complete
    connected = pyqtSignal(bool)        #when scan succeeds/fails
    disconnected = pyqtSignal()         #when device disconnects
    data_received = pyqtSignal(bytes)   #when data is received
    error = pyqtSignal(str)             #when error occurs
    reconnecting = pyqtSignal(int)      #attempt number when reconnecting

    def __init__(self):
        super().__init__()

        #Create manager
        self.manager = USBManager()

        #Which operation to run
        self.operation = None
        self.params = {}

        
        self.running = False    #flag for read loop

        #Auto reconnect settings
        self.connection_timeout = 5.0
        self.auto_reconnect = False
        self.reconnect_attempts = 2
        self.reconnect_delay = 1.0
        self.last_connected_port = None

        #Connect manager signals to worker signals
        self.manager.scan_complete.connect(self.scan_complete.emit)
        self.manager.connected.connect(lambda port: self.connected.emit(True))
        self.manager.disconnected.connect(self.disconnected.emit)
        self.manager.data_received.connect(self.data_received.emit)
        self.manager.error_occurred.connect(self.error.emit)

    #Run in background thread, separate from GUI
    #called when start
    def run(self):
        try:
            #Check operation
            if self.operation == "scan":
                #run scan operation
                self.manager.scan_devices()
            elif self.operation == "connect":
                port = self.params.get('port')
                self.last_connected_port = port   #store port for reconnect
                #run connect operation
                successful = self.manager.connect(port)  #attempt to connect, true if successful
                if successful:
                    self.running = True    #program running
                    self._read_loop()      #start read loop
                else:
                    self.connected.emit(False)    #signal connection failed
            elif self.operation == "disconnect":
                #run disconnect operation
                self.manager.disconnect()
        except Exception as e:
            self.error.emit(f"Error in USB worker: {str(e)}")
            self.running = False    #stop program

    #Read loop while connected
    #read data immediately, emits signal in batches
    def _read_loop(self):
        while self.running and self.manager.is_connected:
            try:
                waiting = self.manager.serial_port.in_waiting    #check if data available
                #if data available, read it
                if waiting > 0:
                    #read data
                    data = self.manager.serial_port.read(waiting)
                    self.data_received.emit(data)    #data received
                else:
                    self.usleep(100)    #small delay to avoid high CPU usage
        
            #if error only when unintentional stop
            except Exception as e:
                if self.running:
                    self.error.emit(f"Error in read loop: {str(e)}")
                break    #stop loop
        
        #if loop ended, but supposed to be running, try reconnect
        if self.running and self.auto_reconnect:
            self.attempt_reconnect()
    
    #Attempt reconnect
    def attempt_reconnect(self):
        port = self.last_connected_port
        #if not stored, cannot reconnect
        if not port:
            self.error.emit("No connected device to reconnect to")
            return
        
        #try reconnect
        for attempt in range(1, self.reconnect_attempts + 1):
            #Emit signal for attempt number
            self.reconnecting.emit(attempt)

            #Wait for delay between attempts
            if attempt > 1:
                self.sleep(self.reconnect_delay)
            
            #Try to connect
            successful = self.manager.connect(port)
            if successful:
                self._read_loop()    #start read loop
                return True    #successful reconnect
            else:
                self.error.emit(f"Reconnect attempt {attempt} failed")

        #if all attempts failed, emit error
        self.running = False    #stop program
        self.error.emit(f"Reconnect failed after {self.reconnect_attempts} attempts")
        self.disconnected.emit()    #signal device disconnected
        return False    #failed

    #Scan for available ports
    def scan(self):
        self.operation = "scan"
        self.start()
       
    #Connect to port
    def connect(self, port):
        self.operation = "connect"
        self.params = {'port': port}
        self.start()

    #Disconnect from port
    def disconnect(self):
        self.running = False               #stop program
        self.auto_reconnect = False        #disable auto reconnect
        self.last_connected_port = None    #clear stored port
        self.manager.disconnect()          #disconnect from port
    

    #Auto reconnect enable/disable
    def set_auto_reconnect(self, enabled):
        self.auto_reconnect = enabled

    #Set auto reconnect attempts
    def set_reconnect_attempts(self, attempts):
        self.reconnect_attempts = attempts
    
    #Set delay between attempts
    def set_reconnect_delay(self, delay):
        self.reconnect_delay = delay
