"""
Device selection
Shows dropdown list of discovered Bluetooth devices
User selects device to connect to
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QComboBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from utils.bluetooth_manager import BluetoothWorker
from utils.usb_manager import USBWorker

#Window for selecting Bluetooth device
class DeviceSelection(QDialog):

    #when user selects and confirms device
    device_selected = pyqtSignal(str)           #address
    usb_device_selected = pyqtSignal(str, int)  #port name, baud rate

    def __init__(self, connection_type, parent=None):    #no parent by default
        super().__init__(parent)

        self.connection_type = connection_type  #bluetooth or usb
        self.devices = []               #list for devices
        self.selected_device = None     #store selected device
        self.is_scanning = False        #track if scanning

        #Create worker based on connection type
        if self.connection_type == "bluetooth":
            self.worker = BluetoothWorker()
        else:
            self.worker = USBWorker()
        
        self.worker.scan_complete.connect(self.on_scan_complete)
        self.worker.error.connect(self.on_error)

        self.init_ui()

        #Start scan automatically
        QTimer.singleShot(100, self.start_scan)
    
    #Initialize UI
    def init_ui(self):
        
        #Settings
        if self.connection_type == "bluetooth":
            self.setWindowTitle("Select Bluetooth Device")
        else:
            self.setWindowTitle("Select USB Device")
        self.setMinimumHeight(550)
        self.setMinimumWidth(200)

        #Stay on top of parent window
        #set flag in dialog window for staying on top of others, dialog flag and on top flag added
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        self.setStyleSheet("background-color: #FAFAFA;")

        #Vertical stack
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        #Title
        title_text = "Select Bluetooth Device" if self.connection_type == "bluetooth" else "Select USB Device"
        title = QLabel(title_text)
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: 600;
                color: #1A1A1A;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        #Subtitle
        subtitle = QLabel("Choose a device to connect to:")
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #1A1A1A;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        #Scanning indicator
        self.create_scanning_widget(layout)

        #Label for dropdown
        device_label_text = "Available Devices:" if self.connection_type == "bluetooth" else "Available Ports:"
        device_label = QLabel(device_label_text)
        device_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #1A1A1A;
                font-weight: 500;
            }
        """)
        layout.addWidget(device_label)

        #Dropdown menu
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(40)
        self.device_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #1A1A1A;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666666;
                margin-right: 5px;
            }
        """)

        #Placeholder
        if self.connection_type == "bluetooth":
            self.device_combo.addItem("No devices found - Click 'Rescan'")
        else:
            self.device_combo.addItem("No ports found - Click 'Rescan'")
        
        layout.addWidget(self.device_combo)

        #Baud rate selection (USB)
        self.baud_rate_widget = QWidget()
        baud_layout = QVBoxLayout(self.baud_rate_widget)
        baud_layout.setContentsMargins(0, 0, 0, 15)
        baud_layout.setSpacing(5)

        #Baud rate label
        baud_label = QLabel("Baud Rate:")
        baud_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #1A1A1A;
                font-weight: 500;
            }
        """)
        baud_layout.addWidget(baud_label)

        #Baud rate dropdown
        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.setMinimumHeight(40)
        self.baud_rate_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #1A1A1A;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666666;
                margin-right: 5px;
            }
        """)

        #Rates
        baud_rates = ["9600", "19200", "38400", "57600", "115200", "230400", "460800"]
        self.baud_rate_combo.addItems(baud_rates)
        self.baud_rate_combo.setCurrentText("115200")   #assumed default for PIC

        baud_layout.addWidget(self.baud_rate_combo)
        layout.addWidget(self.baud_rate_widget)
        self.baud_rate_widget.raise_()

        #Only show for USB
        if self.connection_type == "bluetooth":
            self.baud_rate_widget.hide()

        layout.addSpacing(25)

        #Rescan
        self.scan_button = QPushButton("Rescan for Devices")
        self.scan_button.setMinimumHeight(40)
        self.scan_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #1A1A1A;
            }
        """)

        #Connect to scan
        self.scan_button.clicked.connect(self.start_scan)
        self.scan_button.hide() #show after first scan completes
        layout.addWidget(self.scan_button)

        #Connect button
        self.connect_button = QPushButton("Connect to Device")
        self.connect_button.setMinimumHeight(40)
        self.connect_button.setEnabled(False)  #disabled until device selection
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #1A1A1A;
            }
        """)

        self.connect_button.clicked.connect(self.on_connect_clicked)
        layout.addWidget(self.connect_button)

        #Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                color: #1A1A1A;
            }
        """)

        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

    #Scanning status indicator
    def create_scanning_widget(self, layout):
        scanning_widget = QWidget()
        scanning_layout = QHBoxLayout(scanning_widget)
        scanning_layout.setContentsMargins(0, 0, 0, 0)
        scanning_layout.setSpacing(8)

        #Status label
        self.scan_status_label = QLabel("Initializing")
        self.scan_status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666666;
                font-style: italic;
            }
        """)

        scanning_layout.addStretch(1)
        scanning_layout.addWidget(self.scan_status_label)
        scanning_layout.addStretch(1)

        layout.addWidget(scanning_widget)
    
    #Start Bluetooth device scan
    def start_scan(self):
        #One scan at a time
        if self.is_scanning:
            return
        
        #Update UI show scanning
        self.is_scanning = True
        self.scan_button.setEnabled(False)  #disable rescan during scan
        self.scan_button.setText("Scanning")
        self.scan_status_label.setText("Scanning for devices")

        #Clear previous devices
        self.devices = []
        self.device_combo.clear()
        self.device_combo.addItem("Scanning")
        self.connect_button.setEnabled(False)   #disable during scan

        #Start scan, no delay for USB
        if self.connection_type == "bluetooth":
            self.worker.scan(timeout=10.0)
        else:
            self.worker.scan()

    #When scan completes
    def on_scan_complete(self, found_devices):
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Rescan for devices")
        self.scan_button.show()

        #Store found devices
        self.devices = found_devices
        self.device_combo.clear()

        #Check for found devices
        if found_devices:
            #Add each device
            for name, address in found_devices:
                display_text = f"{name} ({address})"
                self.device_combo.addItem(display_text)

            #Update status
            if self.connection_type == "bluetooth":
                self.scan_status_label.setText(f"Found {len(found_devices)} devices")
            else:
                self.scan_status_label.setText(f"Found {len(found_devices)} ports")
            self.connect_button.setEnabled(True)
        #No devices found
        else:
            if self.connection_type == "bluetooth":
                self.device_combo.addItem("No devices found - Click 'Rescan'")
                self.scan_status_label.setText("No devices found")
            else:
                self.device_combo.addItem("No ports found - Click 'Rescan'")
                self.scan_status_label.setText("No ports found")
            self.connect_button.setEnabled(False)
    
    #On connect to device
    def on_connect_clicked(self):
        #get current index
        current_index = self.device_combo.currentIndex()

        #Verify valid selection
        if 0 <= current_index and current_index < len(self.devices):
            #get device
            selected = self.devices[current_index]
            device_name, device_address = selected
            self.selected_device = device_address

            #Handle based on connection type
            if self.connection_type == "bluetooth":
                #signal device address for bluetooth
                self.device_selected.emit(device_address)
            else:
                #usb baud rate
                baud_rate = int(self.baud_rate_combo.currentText())
                #set manager baud rate
                self.worker.manager.set_baud_rate(baud_rate)
                #signal device and baud rate for usb
                self.usb_device_selected.emit(device_address, baud_rate)

            #Close dialog
            self.accept()
        else:
            #invalid selection
            pass

    #Error occurs
    def on_error(self, error_message):
        # Reset scanning
        self.is_scanning = False
        self.scan_button.setEnabled(True)
        self.scan_button.setText("Rescan for Devices")
        self.scan_button.show()
        
        # Update status
        self.scan_status_label.setText("Error occurred - Click 'Rescan'")

    #Get selected device
    def get_selected_device(self):
        return self.selected_device
    
    #Get selected baud rate
    def get_selected_baud_rate(self):
        if self.connection_type == "usb":
            return int(self.baud_rate_combo.currentText())
        return None