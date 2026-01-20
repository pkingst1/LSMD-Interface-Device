"""
Data Acquisition - Data display and communication window
Shows data received from connected device
Allows for sending of data to connected device
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

#Data acquisition screen
class DataAcquisitionWindow(QWidget):
    
    #Define signals
    disconnect_request = pyqtSignal()
    send_data = pyqtSignal(str)
    switch_view = pyqtSignal()

    def __init__(self, connection_type, device_address=None, port_name=None, baud_rate=None):    #initialize address to None
        super().__init__()
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.init_ui()

    def init_ui(self):
        #Initialize UI
        self.setWindowTitle("LSMD Data Interface - Data Acquisition")
        self.setMinimumSize(800, 500)

        #Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 0, 5, 30)
        main_layout.setSpacing(15)

        #Top bar
        self.create_top_bar(main_layout)

        #Data display
        self.create_data_display(main_layout)

        #Send data
        self.create_send_section(main_layout)

    #Top bar, battery, connection, disconnect
    def create_top_bar(self, layout):
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        #Battery indicator
        battery_widget = QWidget()
        battery_layout = QHBoxLayout(battery_widget)
        battery_layout.setContentsMargins(0, 0, 0, 0)
        battery_layout.setSpacing(5)

        battery_icon = QLabel("●")
        battery_icon.setStyleSheet("color: #4CAF50; font-size: 10px;")

        battery_text = QLabel("Battery: 67%")
        battery_text.setStyleSheet("color: #666666; font-size: 12px;")

        battery_layout.addWidget(battery_icon)
        battery_layout.addWidget(battery_text)
        battery_widget.setMaximumWidth(150)

        top_bar.addWidget(battery_widget)
        top_bar.addStretch(1)

        #Switch view button
        self.switch_view_button = QPushButton("Switch to Dashboard View")
        self.switch_view_button.clicked.connect(self.on_switch_view_clicked)
        top_bar.addWidget(self.switch_view_button)
        top_bar.addStretch(1)
    

        #Right side
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        #Connection indicator
        if self.connection_type == "bluetooth":
            self.status_indicator = QLabel("Bluetooth Connected")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    background-color: #2196F3;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.status_indicator = QLabel("USB Connected")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    background-color: #B2BEB5;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        
        #Disconnect button
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setMinimumHeight(32)
        self.disconnect_button.setStyleSheet("""
            QPushButton {
                background-color: #DC3545;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        self.disconnect_button.clicked.connect(self.on_disconnect_clicked)

        right_layout.addWidget(self.status_indicator)
        right_layout.addWidget(self.disconnect_button)

        top_bar.addWidget(right_widget)

        layout.addLayout(top_bar)

    #Data display
    def create_data_display(self, layout):

        display_container = QWidget()
        display_layout = QVBoxLayout(display_container)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(5)

        #Header, label and clear data option
        header_layout = QHBoxLayout()
        
        #Label
        data_label = QLabel("Received Data:")
        data_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #f0eded;
            }
        """)
        header_layout.addWidget(data_label)
        header_layout.addStretch(1)

        #Clear button
        clear_button = QPushButton("Clear Display")
        clear_button.setMaximumWidth(120)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #424242;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
        """)
        clear_button.clicked.connect(self.clear_display)
        header_layout.addWidget(clear_button)

        display_layout.addLayout(header_layout)

        #Text display
        self.data_display = QTextEdit()
        self.data_display.setReadOnly(True)
        self.data_display.setMinimumHeight(300)
        self.data_display.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
                color: #1A1A1A;
            }
        """)
        self.data_display.setPlaceholderText("Waiting for data")    #Placeholder

        display_layout.addWidget(self.data_display)

        layout.addWidget(display_container)

    #Send data
    def create_send_section(self, layout):
        
        send_container = QWidget()
        send_layout = QVBoxLayout(send_container)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(5)

        #Label
        send_label = QLabel("Send data:")
        send_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #f0eded;
            }
        """)
        send_layout.addWidget(send_label)

        #Input and button
        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        
        #Data input
        self.data_input = QLineEdit()
        self.data_input.setPlaceholderText("Enter data to send")
        self.data_input.setMinimumHeight(44)
        self.data_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 2px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                color: #1A1A1A;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)

        input_layout.addWidget(self.data_input)

        #Send button
        send_button = QPushButton("Send")
        send_button.setMinimumWidth(100)
        send_button.setMinimumHeight(44)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
        """)
        send_button.clicked.connect(self.on_send_clicked)

        input_layout.addWidget(send_button)
        send_layout.addLayout(input_layout)
        layout.addWidget(send_container)

    #Append received data
    def append_data(self, data):
        #Convert bytes to String
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')     #show decoded string
            except:                 
                data = data.hex()               #show hex

        self.data_display.append(data)

    #Clear data display
    def clear_display(self):
        self.data_display.clear()

    #Send button interaction
    def on_send_clicked(self):
        data_to_send = self.data_input.text().strip()   #get text

        #check for data
        if data_to_send:
            self.send_data.emit(data_to_send)   #emit signal
            self.data_input.clear()             #clear for next message
            self.data_display.append(f">Sent: {data_to_send}")  #show sent message

    #Disconnect button interaction
    def on_disconnect_clicked(self):
        self.disconnect_request.emit()

    def on_switch_view_clicked(self):
        self.switch_view.emit()