"""
Data Acquisition Dashboard- Data display and communication window
Shows data received from connected device
Allows for sending of data to connected device
Shows data in a dashboard format
Allows for switching with testing data acquisition window
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

#Data acquisition dashboard screen
class DataAcquisitionDashboard(QWidget):

    #Define signals
    send_data = pyqtSignal(str)
    switch_view = pyqtSignal()
    disconnect_request = pyqtSignal()

    def __init__(self, connection_type, device_address=None, port_name=None, baud_rate=None):    #initialize address to None
        super().__init__()
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.is_acquiring = False
        self.init_ui()
    
    #Initialize UI
    def init_ui(self):
        self.setWindowTitle("LSMD Data Interface - Data Acquisition Dashboard")
        self.setMinimumSize(800, 500)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 0, 5, 30)
        main_layout.setSpacing(15)

        self.create_top_bar(main_layout)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        self.create_pager_header(content_layout)
        self.create_acquisition_control(content_layout)
        content_layout.addStretch(1)

        main_layout.addLayout(content_layout)

    #Top bar, battery, switch view, connection, disconnect
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
        self.switch_view_button = QPushButton("Switch to Debug View")
        self.switch_view_button.clicked.connect(self.on_switch_view_clicked)
        top_bar.addWidget(self.switch_view_button)
        top_bar.addStretch(1)

        #Right side
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

    #Pager header
    def create_pager_header(self, layout):
        title = QLabel("Data Acquisition Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle = QLabel("Real-time torque measurement and analysis")
        subtitle.setStyleSheet("font-size: 14px; color: #666666;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
    #Acquisition controls
    def create_acquisition_control(self, layout):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setFixedWidth(200)
        card.setFixedHeight(120)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        #Card header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QLabel("▶")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px;")
        title_label = QLabel("Acquisition Control")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)

        #Start stop buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.start_button = QPushButton("Start")
        self.start_button.setCheckable(True)
        self.start_button.setChecked(False)
        self.start_button.clicked.connect(self.on_start_clicked)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setCheckable(True)
        self.stop_button.setChecked(False)
        self.stop_button.clicked.connect(self.on_stop_clicked)

        #Update button styles based on acquisition state
        self.update_button_styles()

        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        card_layout.addLayout(button_layout)
        layout.addWidget(card)

    #Start clicked
    def on_start_clicked(self):
        if not self.is_acquiring:
            self.is_acquiring = True
            self.start_button.setChecked(True)
            self.stop_button.setChecked(False)
            self.update_button_styles()
            self.send_data.emit("START")
            print("Acquisition started")
    
    #Stop clicked
    def on_stop_clicked(self):
        if self.is_acquiring:
            self.is_acquiring = False
            self.start_button.setChecked(False)
            self.stop_button.setChecked(True)
            self.update_button_styles()
            self.send_data.emit("STOP")
            print("Acquisition stopped")
    
    #Update button styles based on acquisition state
    def update_button_styles(self):
        #Acquiring state
        if self.is_acquiring:
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #1A1A1A;
                    color: white;
                    border: none;
                    border-radius: 6px 0px 0px 6px;
                    padding: 12px 24px;
                }
            """)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #666666;
                    border: none;
                    border-radius: 0px 6px 6px 0px;
                    padding: 12px 24px;
                }
            """)
        #Not acquiring state
        else:
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #666666;
                    border: none;
                    border-radius: 6px 0px 0px 6px;
                    padding: 12px 24px;
                }
            """)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #1A1A1A;
                    color: white;
                    border: none;
                    border-radius: 0px 6px 6px 0px;
                    padding: 12px 24px;
                }
            """)
    
    #Switch view button clicked
    def on_switch_view_clicked(self):
        self.switch_view.emit()

    #Disconnect button clicked
    def on_disconnect_clicked(self):
        if self.is_acquiring:
            self.on_stop_clicked()
        self.disconnect_request.emit()
        print("Disconnected from device")
    
    #Data display (placeholder in console for now)
    def append_data(self, data):
        #For now, just print to console
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except:
                data = data.hex()
        print(f"Received data: {data}")     #Placeholder for data display
