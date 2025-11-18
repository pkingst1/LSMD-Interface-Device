"""
LSMD Data Interface - Main Application
Run this file to start the program
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from windows.connection_window import ConnectionWindow
from windows.device_selection import DeviceSelection
from windows.data_acquisition import DataAcquisitionWindow
from utils.bluetooth_manager import BluetoothWorker

#Main Application Controller
class LSMDApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_application()

        #Reference to window
        self.connection_window = None
        self.device_selection_window = None
        self.data_acquisition_window = None

        #Bluetooth worker for connections
        self.bluetooth_worker = None
        self.connected_device_address = None

        #Show connection window
        self.show_connection_window()
    
    #Application settings
    def setup_application(self):
        font = QFont("Segoe UI", 10)
        self.app.setFont(font)
        self.app.setStyle("Fusion")

    #Connection window screen
    def show_connection_window(self):
        self.connection_window = ConnectionWindow()

        self.connection_window.usb_selected.connect(self.on_usb_connection)
        self.connection_window.bluetooth_selected.connect(self.on_bluetooth_connection)
        
        self.connection_window.show()
    
    #USB connection
    def on_usb_connection(self):
        print("USB selected")
    
    #Bluetooth connection
    def on_bluetooth_connection(self):
        print("Bluetooth selected")

        #Show device selection dialog
        self.device_selection_window = DeviceSelection(parent=self.connection_window)
        
        #Connect the device selected signal to handler
        self.device_selection_window.device_selected.connect(self.on_device_selected)

        #Block interaction with parent window
        result = self.device_selection_window.exec()

        #Check if user cancelled
        if result == DeviceSelection.DialogCode.Rejected:
            self.connection_window.update_connection_status(None)
    
    #User selects device from window
    def on_device_selected(self, device_address):
        #Store address
        self.connected_device_address = device_address

        #Check and create Bluetooth worker
        if self.bluetooth_worker is None:
            self.bluetooth_worker = BluetoothWorker()

            #Connect worker to handler
            self.bluetooth_worker.connected.connect(self.on_bluetooth_connected)
            self.bluetooth_worker.disconnected.connect(self.on_bluetooth_disconnected)
            self.bluetooth_worker.error.connect(self.on_bluetooth_error)

            #Connect data received
            self.bluetooth_worker.manager.data_received.connect(self.on_data_received)

        #Connection
        self.bluetooth_worker.connect(device_address)
    #Connection succeeds
    def on_bluetooth_connected(self, success):
        if success:
            print(f"Successfully connected to Bluetooth device: {self.connected_device_address}")

            #hide connection window
            self.connection_window.hide()
            #show data acquisition window
            self.show_data_acquisition_window()

        else:
            print("Failed to connect to Bluetooth device")
            #Reset connection status
            self.connection_window.update_connection_status(None)

    #Show data acquisition window after successful connection
    def show_data_acquisition_window(self):
        #Create data acquisition window
        self.data_acquisition_window = DataAcquisitionWindow(
            device_address=self.connected_device_address)
        
        #Connect signals
        #disconnect
        self.data_acquisition_window.disconnect_request.connect(self.on_disconnect_request)
        #send
        self.data_acquisition_window.send_data.connect(self.on_send_data)

        self.data_acquisition_window.show()

    #Data received
    def on_data_received(self, data):
        #check for acquisition window, display data
        if self.data_acquisition_window:
            self.data_acquisition_window.append_data(data)
    
    #Send data
    def on_send_data(self, data):
        #check for bluetooth worker, send data
        if self.bluetooth_worker:
            self.bluetooth_worker.send(data)
    
    #User selects disconnect
    def on_disconnect_request(self):
        #close bluetooth worker
        if self.bluetooth_worker:
            self.bluetooth_worker.disconnect_device()
        
        #close data acquisition window
        if self.data_acquisition_window:
            self.data_acquisition_window.close()
            self.data_acquisition_window = None
        
        #show connection window again
        self.connection_window.show()
        self.connection_window.update_connection_status(None)

    #Bluetooth disconnects
    def on_bluetooth_disconnected(self):
        print(f"Bluetooth device disconnected")
        self.connected_device_address = None
        self.connection_window.update_connection_status(None)

    #Error occurs
    def on_bluetooth_error(self, error_message):
        print(f"Bluetooth error: {error_message}")


    #Event loop
    def run(self):
        return self.app.exec()
    
#Main app
def main():
    app = LSMDApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()