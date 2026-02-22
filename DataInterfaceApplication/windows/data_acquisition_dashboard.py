"""
Data Acquisition Dashboard- Data display and communication window
Shows data received from connected device
Allows for sending of data to connected device
Shows data in a dashboard format
Allows for switching with testing data acquisition window
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit, QScrollArea, QFrame, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from collections import deque

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
        

        #Data storage for plotting - 10 seconds at 1000Hz = 10,000 points max
        self.sample_rate = 1200  # Hz
        self.max_duration = 10   # seconds
        self.max_data_points = self.sample_rate * self.max_duration
        self.time_data = deque(maxlen=self.max_data_points)
        self.force_data = deque(maxlen=self.max_data_points)
        self.data_point_count = 0
        self.data_buffer = ""    #Buffer for incomplete data
        
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
        self.create_graph_display(content_layout)
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

    #Data cards
    def create_data_cards(self, layout):
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        # Card 1: Acquisition Control
        self.create_acquisition_control_card(cards_layout)
        
        # Card 2: placeholder for now
        self.create_empty_card(cards_layout)
        
        # Card 3: placeholder for now
        self.create_empty_card(cards_layout)
        
        layout.addLayout(cards_layout)

    #Acquisition control card
    def create_acquisition_control(self, layout):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(140)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        #Card header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QLabel("▶")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Acquisition Control")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)

        #Start stop buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(0)

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
        card_layout.addStretch(1)
        layout.addWidget(card)

    #Empty placeholder card
    def create_empty_card(self, layout):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(140)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        card_layout.addStretch(1)
        
        layout.addWidget(card)

    #Graph display
    def create_graph_display(self, layout):
        graph_card = QFrame()
        graph_card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)
        
        graph_layout = QVBoxLayout(graph_card)
        graph_layout.setContentsMargins(16, 16, 16, 16)
        graph_layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title_label = QLabel("Force vs Time")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        
        subtitle_label = QLabel("Real-time force measurement display")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch(1)
        
        graph_layout.addLayout(header_layout)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(10, 4), facecolor='white')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Style the plot
        self.ax.set_xlabel('Time (s)', fontsize=10, color='#666666')
        self.ax.set_ylabel('Force (N)', fontsize=10, color='#666666')
        self.ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
        self.ax.set_facecolor('#FAFAFA')
        
        # Initialize empty plot
        self.line, = self.ax.plot([], [], color='#2196F3', linewidth=2)
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 1000)
        
        self.figure.tight_layout()
        
        graph_layout.addWidget(self.canvas)
        
        layout.addWidget(graph_card)

    
    #Start clicked
    def on_start_clicked(self):
        if not self.is_acquiring:
            self.is_acquiring = True
            self.start_button.setChecked(True)
            self.stop_button.setChecked(False)
            self.update_button_styles()

            #Clear data
            self.time_data.clear()
            self.force_data.clear()
            self.data_point_count = 0

            #Send start command
            self.send_data.emit("START\n")
            print("Acquisition started")
    
    #Stop clicked
    def on_stop_clicked(self):
        if self.is_acquiring:
            self.is_acquiring = False
            self.start_button.setChecked(False)
            self.stop_button.setChecked(True)
            self.update_button_styles()

            self.send_data.emit("STOP\n")
            print("Acquisition stopped")
            print(f"Data points: {self.data_point_count}")
    
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
    
    #Data display, receive data and updates plot
    def append_data(self, data):
        if not self.is_acquiring:
            return
        
        # Convert bytes to string
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except:
                print(f"Could not decode data: {data}")
                return
        
        # Add to buffer
        self.data_buffer += data
        
        # Process complete lines
        while '\n' in self.data_buffer:
            line, self.data_buffer = self.data_buffer.split('\n', 1)
            line = line.strip()
            
            if not line:
                continue
            
            # Check for max duration
            if self.data_point_count >= self.max_data_points:
                print(f"Maximum data points reached ({self.max_data_points}). Stopping acquisition.")
                self.on_stop_clicked()
                return
            
            # Try to parse as float
            try:
                force_value = float(line)
                
                # Calculate time based on sample rate
                time_value = self.data_point_count / self.sample_rate
                
                self.time_data.append(time_value)
                self.force_data.append(force_value)
                self.data_point_count += 1
                
                # Update plot every 100 points
                if self.data_point_count % 100 == 0:
                    self.update_plot()
                    
            except ValueError:
                print(f"Could not parse: {line}")
        
    def update_plot(self):
        if len(self.time_data) > 0:
            self.line.set_data(list(self.time_data), list(self.force_data))

            #Auto-scale x-axis as data acquired, max 10 seconds
            max_time = max(self.time_data)
            self.ax.set_xlim(0, min(10, max(max_time * 1.1, 1)))

            #Auto-scale y-axis
            if len(self.force_data) > 0:
                min_force = min(self.force_data)
                max_force = max(self.force_data)
                margin = (max_force - min_force) * 0.1 if max_force > min_force else 100
                self.ax.set_ylim(max(0, min_force - margin), max_force + margin)
            
            self.canvas.draw()