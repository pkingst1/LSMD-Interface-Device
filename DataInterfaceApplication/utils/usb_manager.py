"""
USB Manager - Handles USB connections using pyserial library
"""

#Add serial library
import serial
import serial.tools.list_ports
from PyQt6.QtCore import QObject, pyqtSignal

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

        except Exception as e:
            error_msg = f"Scan error: {str(e)}"
            self.error_occurred.emit(error_msg)
            return  []       #return empty list if error

    #Connect to port
    def connect_to_port(self, port_name):
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
    def disconnect_from_port(self):
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
            return False                        #Failed to disconnect