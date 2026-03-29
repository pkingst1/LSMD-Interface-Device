"""
LSMD Data Interface - Main Application
Run this file to start the program
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (QFont, QPalette, QColor)

from windows.connection_window import ConnectionWindow
from windows.device_selection import DeviceSelection
from windows.data_acquisition import DataAcquisitionWindow
from windows.data_acquisition_dashboard import DataAcquisitionDashboard
from windows.calibration_window import CalibrationWindow
from windows.settings_window import SettingsWindow
from utils.bluetooth_manager import BluetoothWorker
from utils.usb_manager import USBWorker
from utils.zero_calibration import ZeroCalibration

#Main Application Controller
class LSMDApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.setup_application()

        #Reference to window
        self.connection_window = None
        self.device_selection_window = None
        self.data_acquisition_window = None
        self.settings_window = None
        self.calibration_window = None

        #Track view type
        self.using_dashboard = True

        #Bluetooth worker for connections
        self.bluetooth_worker = None
        self.connected_device_address = None

        #USB worker for connections
        self.usb_worker = None
        self.connected_port = None
        self.connected_baud_rate = None

        #Zero calibration for force measurements
        self.zero_calibration = ZeroCalibration()

        #Track connection type
        self.connection_type = None

        #Show connection window
        self.show_connection_window()
    
    #Application settings
    def setup_application(self):
        font = QFont("Segoe UI", 10)
        self.app.setFont(font)
        self.app.setStyle("Fusion")

        #Override OS theme
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        self.app.setPalette(palette)

    #Connection window screen
    def show_connection_window(self):
        self.connection_window = ConnectionWindow()

        self.connection_window.usb_selected.connect(self.on_usb_connection)
        self.connection_window.bluetooth_selected.connect(self.on_bluetooth_connection)
        
        self.connection_window.show()
    
    #USB connection
    def on_usb_connection(self):
        print("USB selected")

        #Show device selection dialog
        self.device_selection_window = DeviceSelection(connection_type="usb", parent=self.connection_window)

        #Connect the device selected signal to handler
        self.device_selection_window.usb_device_selected.connect(self.on_usb_device_selected)

        #Block interaction with parent window
        result = self.device_selection_window.exec()

        #Check if user cancelled
        if result == DeviceSelection.DialogCode.Rejected:
            self.connection_window.update_connection_status(None)
    
    #Bluetooth connection
    def on_bluetooth_connection(self):
        print("Bluetooth selected")

        #Show device selection dialog
        self.device_selection_window = DeviceSelection(connection_type="bluetooth",parent=self.connection_window)
        
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
        self.connection_type = "bluetooth"

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
            self._saved_geometry = self.connection_window.geometry() #Save size
            #show data acquisition window
            self.show_data_acquisition_window()

        else:
            print("Failed to connect to Bluetooth device")
            #Reset connection status
            self.connection_window.update_connection_status(None)

    #Show data acquisition window after successful connection
    def show_data_acquisition_window(self):
        if self.using_dashboard:
            #Initialize dashboard view
            #Create based on connection type
            if self.connection_type == "bluetooth":
                self.data_acquisition_window = DataAcquisitionDashboard(connection_type="bluetooth", device_address=self.connected_device_address)
            else:
                self.data_acquisition_window = DataAcquisitionDashboard(connection_type="usb", port_name=self.connected_port, baud_rate=self.connected_baud_rate)

            #connect switch view signal
            self.data_acquisition_window.switch_view.connect(self.on_switch_view)
            self.data_acquisition_window.navigate_to_settings.connect(self.on_navigate_to_settings)
            self.data_acquisition_window.clear_data_selected.connect(self.on_clear_data_filters)
        
        #Debug view
        else:
            #Create based on connection type
            if self.connection_type == "bluetooth":
                self.data_acquisition_window = DataAcquisitionWindow(connection_type="bluetooth", device_address=self.connected_device_address)
            else:
                self.data_acquisition_window = DataAcquisitionWindow(connection_type="usb", port_name=self.connected_port, baud_rate=self.connected_baud_rate)

            #connect switch view signal
            self.data_acquisition_window.switch_view.connect(self.on_switch_view)

        #Connect signals
        #disconnect
        self.data_acquisition_window.disconnect_request.connect(self.on_disconnect_request)
        #send
        self.data_acquisition_window.send_data.connect(self.on_send_data)

        self.data_acquisition_window.show()
        self.data_acquisition_window.setGeometry(self._saved_geometry) #Restore size

    #Navigate to settings
    def on_navigate_to_settings(self):
        #Hide dashboard, do not destory
        if self.data_acquisition_window:
            self._saved_geometry = self.data_acquisition_window.geometry() #Save size
            self.data_acquisition_window.hide()

        #Create settings window only if not already created
        if self.settings_window is None:
            if self.connection_type == "bluetooth":
                self.settings_window = SettingsWindow(connection_type="bluetooth", device_address=self.connected_device_address)
            else:
                self.settings_window = SettingsWindow(connection_type="usb", port_name=self.connected_port, baud_rate=self.connected_baud_rate)
        
            #Connect signals once only
            self.settings_window.navigate_to_dashboard.connect(self.on_navigate_to_dashboard)
            self.settings_window.disconnect_request.connect(self.on_disconnect_request)
            self.settings_window.filter_settings_changed.connect(self.on_filter_settings_changed)
            self.settings_window.navigate_to_calibration.connect(self.on_navigate_to_calibration)
            self.settings_window.auto_reconnect_changed.connect(self.on_auto_reconnect_changed)


        self.settings_window.setGeometry(self._saved_geometry) #Restore size
        self.settings_window.show()
    
    #Filter settings changed
    def on_filter_settings_changed(self):
        if self.settings_window and self.data_acquisition_window:
            filters = self.settings_window.get_active_filters(
            self.data_acquisition_window.sample_rate
            )
        self.data_acquisition_window.apply_filter(filters)
        
    #Navigate back to dashboard
    def on_navigate_to_dashboard(self):
        #Gide settings window
        if self.settings_window:
            self._saved_geometry = self.settings_window.geometry() #Save size and location
            self.settings_window.hide()
        
        #Re-apply filter state before showing dashboard
        self.on_filter_settings_changed()
        
        #Show existing dashboard window
        if self.data_acquisition_window:
            self._saved_geometry = self.data_acquisition_window.geometry() #Save size and location
            self.data_acquisition_window.show()
    
    #Switch view
    def on_switch_view(self):
        #Toggle view type
        self.using_dashboard = not self.using_dashboard
        #Close current window
        if self.data_acquisition_window:
            self.data_acquisition_window.close()
            self.data_acquisition_window = None
        
        #Show dashboard view
        self.show_data_acquisition_window()

    #Navigate to calibraton panel (overlay settings)
    def on_navigate_to_calibration(self):
        if self.settings_window:
            self._saved_geometry = self.settings_window.geometry()
            self.settings_window.hide()

        if self.calibration_window is None:
            self.calibration_window = CalibrationWindow(
                connection_type=self.connection_type,
                device_address=self.connected_device_address,
                port_name=self.connected_port,
                baud_rate=self.connected_baud_rate,
                sample_rate=self.data_acquisition_window.sample_rate
            )
            self.calibration_window.navigate_to_settings.connect(self.on_navigate_to_settings_from_calibration)
            self.calibration_window.navigate_to_dashboard.connect(self.on_navigate_to_dashboard_from_calibration)
            self.calibration_window.disconnect_request.connect(self.on_disconnect_request)
            self.calibration_window.send_data.connect(self.on_send_data)
            self.calibration_window.zero_calibration_complete.connect(self.on_zero_calibration_complete)
            self.calibration_window.zero_status_updated.connect(self.on_zero_status_updated)

        self.calibration_window.setGeometry(self._saved_geometry)
        self.calibration_window.show()

    #Navigate back to settings from calibration
    def on_navigate_to_settings_from_calibration(self):
        if self.calibration_window:
            self._saved_geometry = self.calibration_window.geometry()
            self.calibration_window.hide()

        if self.settings_window:
            self.settings_window.setGeometry(self._saved_geometry)
            self.settings_window.show()

    #Navigate to dashboard from calibration (skips settings)
    def on_navigate_to_dashboard_from_calibration(self):
        if self.calibration_window:
            self._saved_geometry = self.calibration_window.geometry()
            self.calibration_window.hide()

        if self.data_acquisition_window:
            self.data_acquisition_window.setGeometry(self._saved_geometry)
            self.data_acquisition_window.show()

    #Data received
    def on_data_received(self, data):
        #Route to calibration window if zero calibration is collecting
        if self.calibration_window and self.calibration_window.is_zero_collecting:
            self.calibration_window.append_zero_calibration_data(data)
            return

        #Route to calibration window if five point calibration is collecting
        if self.calibration_window and self.calibration_window.is_five_point_collecting:
            self.calibration_window.append_five_point_calibration_data(data)
            return

        #Normal data flow to acquisition window
        if self.data_acquisition_window:
            self.data_acquisition_window.append_data(data)
    
    #Send data
    def on_send_data(self, data):
        #check for connection type and send data
        if self.connection_type == "bluetooth" and self.bluetooth_worker:
            self.bluetooth_worker.send(data)
        elif self.connection_type == "usb" and self.usb_worker:
            self.usb_worker.manager.send_data(data)
    
    #User selects disconnect
    def on_disconnect_request(self):
        #Save geometry of current visible window
        if self.data_acquisition_window:
            self._saved_geometry = self.data_acquisition_window.geometry()
        elif self.settings_window:
            self._saved_geometry = self.settings_window.geometry()

        #Close worker based on connection type
        if self.connection_type == "bluetooth" and self.bluetooth_worker:
            self.bluetooth_worker.disconnect_device()
        elif self.connection_type == "usb" and self.usb_worker:
            self.usb_worker.disconnect()
        
        #close data acquisition window
        if self.data_acquisition_window:
            self.data_acquisition_window.close()
            self.data_acquisition_window = None
        
        #close settings window
        if self.settings_window:
            self.settings_window.close()
            self.settings_window = None

        #close calibration window
        if self.calibration_window:
            self.calibration_window.close()
            self.calibration_window = None
        
        #Reset connection type
        self.connection_type = None

        #Show connection window again and restore geometry
        self.connection_window.setGeometry(self._saved_geometry)
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

    #User selects USB device
    def on_usb_device_selected(self, port_name, baud_rate):
        #Store port and baud rate
        self.connected_port = port_name
        self.connected_baud_rate = baud_rate
        self.connection_type = "usb"

        #Check and create USB worker
        if self.usb_worker is None:
            self.usb_worker = USBWorker()

            #Connect to handler
            self.usb_worker.connected.connect(self.on_usb_connected)
            self.usb_worker.disconnected.connect(self.on_usb_disconnected)
            self.usb_worker.error.connect(self.on_usb_error)

            #Connect data recieved
            self.usb_worker.data_received.connect(self.on_data_received)
        
        #Connection
        self.usb_worker.manager.set_baud_rate(baud_rate)
        self.usb_worker.connect(port_name)
    
    #USB connection succeeds
    def on_usb_connected(self, success):
        if success:
            print(f"Successfully connected to USB device: {self.connected_port}")
            #Hide connection window
            self.connection_window.hide()
            self._saved_geometry = self.connection_window.geometry() #Save size
            #Show data acquisition window
            self.show_data_acquisition_window()
        else:
            print("Failed to connect to USB device")
            #Reset connection
            self.connection_window.update_connection_status(None)

    #USB disconnects
    def on_usb_disconnected(self):
        print(f"USB device disconnected")
        self.connected_port = None
        self.connected_baud_rate = None
        self.connection_window.update_connection_status(None)
    
    #USB error
    def on_usb_error(self, error_message):
        print(f"USB error: {error_message}")

    def on_clear_data_filters(self):
        if self.settings_window:
            self.settings_window.reset_filters()

    #Zero calibration complete - store offset and forward to dashboard
    def on_zero_calibration_complete(self, offset):
        self.zero_calibration.zero_offset = offset
        self.zero_calibration.is_calibrated = True
        print(f"Zero calibration stored — offset: {offset:.2f}")

        #Apply to dashboard if it exists
        if self.data_acquisition_window:
            self.data_acquisition_window.zero_offset = offset
    
    #Update zero calibration status on settings card
    def on_zero_status_updated(self, offset, is_calibrated):
        if self.settings_window:
            self.settings_window.update_zero_status(offset, is_calibrated)

    #Auto reconnect changed
    def on_auto_reconnect_changed(self, enabled):
        if self.connection_type == "bluetooth" and self.bluetooth_worker:
            self.bluetooth_worker.set_auto_reconnect_enable(enabled)
        elif self.connection_type == "usb" and self.usb_worker:
            self.usb_worker.set_auto_reconnect(enabled)
    
#Main app
def main():
    app = LSMDApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()