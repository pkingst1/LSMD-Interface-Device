"""
Data Acquisition Dashboard- Data display and communication window
Shows data received from connected device
Allows for sending of data to connected device
Shows data in a dashboard format
Allows for switching with testing data acquisition window
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout,  QLineEdit, QFrame, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import pyqtgraph as pg
import numpy as np
from collections import deque
import time
import pandas as pd

#Data acquisition dashboard screen
class DataAcquisitionDashboard(QWidget):

    #Define signals
    send_data = pyqtSignal(str)
    switch_view = pyqtSignal()
    disconnect_request = pyqtSignal()
    navigate_to_settings = pyqtSignal()
    clear_data_selected = pyqtSignal()

    def __init__(self, connection_type, device_address=None, port_name=None, baud_rate=None):    #initialize address to None
        super().__init__()
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.is_acquiring = False
        

        #Data storage for plotting - 10 seconds at 600Hz = 12,000 points max
        self.sample_rate = 1200  # Hz
        self.max_duration = 10   # seconds
        self.max_data_points = self.sample_rate * self.max_duration
        self.raw_force_data = deque(maxlen=self.max_data_points) #unfiltered force data
        self.time_data = deque(maxlen=self.max_data_points)
        self.force_data = deque(maxlen=self.max_data_points)
        self.data_point_count = 0
        self.data_buffer = ""    #Buffer for incomplete data
        self.acquisition_start_time = None
        self.x_axis_max = 1
        self.acquisition_timer = QTimer()
        self.acquisition_timer.setSingleShot(True)
        self.acquisition_timer.timeout.connect(self._on_acquisition_timeout)
        self.rate_start_line = None
        self.rate_end_line = None

        self.peak_torque = 0.0  #peak torque value for export (N·m)
        self.rtd = None        #rate of torque development for export (N·m/s), None if not calculated

        self.zero_offset = 0.0
        self.piecewise_cal = None

        self.settings_window = None  #set for limb length access
        
        self.init_ui()

    #Initialize UI
    def init_ui(self):
        self.setWindowTitle("LSMD Data Interface - Data Acquisition Dashboard")
        self.setMinimumSize(1100, 700)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 30)
        main_layout.setSpacing(0)

        self.create_top_bar(main_layout)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        self.create_pager_header(content_layout)
        self.create_data_cards(content_layout)
        self.create_graph_display(content_layout)
        self.create_stats_cards(content_layout)
        content_layout.addStretch(1)

        main_layout.addLayout(content_layout)

    #Top bar, battery, switch view, connection, disconnect
    def create_top_bar(self, layout):
        #Row 1: Battery, connection status
        row1_container = QWidget()
        row1_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border-radius: 0px;
            }
        """)
        row1_container_layout = QVBoxLayout(row1_container)
        row1_container_layout.setContentsMargins(5, 6, 5, 6)
        row1_container_layout.setSpacing(0)

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)

        #Battery indicator
        battery_widget = QWidget()
        battery_layout = QHBoxLayout(battery_widget)
        battery_layout.setContentsMargins(0, 0, 0, 0)
        battery_layout.setSpacing(5)

        battery_icon = QLabel("●")
        battery_icon.setStyleSheet("color: #4CAF50; font-size: 11px;")

        battery_text = QLabel("Battery: 67%")
        battery_text.setStyleSheet("color: #666666; font-size: 11px;")

        battery_layout.addWidget(battery_icon)
        battery_layout.addWidget(battery_text)
        battery_widget.setMaximumWidth(150)

        row1.addWidget(battery_widget)
        row1.addStretch(1)

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

        row1.addWidget(self.status_indicator)

        #Row 2: Navigation, debug view, disconnect
        row2_container = QWidget()
        row2_container.setStyleSheet("""
            QWidget {
                background-color: #3A3A3A;
                border-radius: 0px;
            }
        """)
        row2_container_layout = QVBoxLayout(row2_container)
        row2_container_layout.setContentsMargins(5, 6, 5, 6)
        row2_container_layout.setSpacing(0)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)

        #Navigation ticker (Data Acquisition - Settings)
        navigation_widget = QWidget()
        navigation_layout = QHBoxLayout(navigation_widget)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(0)

        self.dashboard_tab = QPushButton("Dashboard")
        self.dashboard_tab.setFixedHeight(32)
        self.dashboard_tab.setMinimumWidth(100)
        self.dashboard_tab.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: white;
                border: 1px solid #1A1A1A;
                border-radius: 6px 0px 0px 6px;
                padding: 6px 18px;
                font-size: 11px;
                font-weight: 500;
            }
        """)

        self.settings_tab = QPushButton("Settings")
        self.settings_tab.setFixedHeight(32)
        self.settings_tab.setMinimumWidth(100)
        self.settings_tab.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 0px 6px 6px 0px;
                padding: 6px 18px;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self.settings_tab.clicked.connect(self.on_settings_clicked)

        navigation_layout.addWidget(self.dashboard_tab)
        navigation_layout.addWidget(self.settings_tab)

        row2.addWidget(navigation_widget)
        row2.addStretch(1)
        
        """
        ---------------
        Uncomment this section to add back the switch view button
        ---------------
        
        #Switch view button
        self.switch_view_button = QPushButton("Switch to Debug View")
        self.switch_view_button.setMinimumHeight(32)
        self.switch_view_button.setStyleSheet("""
            #QPushButton {
               # font-size: 11px;
               # font-weight: 500;
           # }
        """)
        self.switch_view_button.clicked.connect(self.on_switch_view_clicked)
        row2.addWidget(self.switch_view_button)
        """
        row2.addStretch(1)

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

        row2.addWidget(self.disconnect_button)

        row1_container_layout.addLayout(row1)
        row2_container_layout.addLayout(row2)
        layout.addWidget(row1_container)
        layout.addWidget(row2_container)

    #Pager header
    def create_pager_header(self, layout):
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("Data Acquisition Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle = QLabel("Real-time torque measurement and analysis")
        subtitle.setStyleSheet("font-size: 14px; color: #666666;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_widget)

    #Data cards
    def create_data_cards(self, layout):
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        #Card 1: Acquisition Control
        card1 = self.create_acquisition_control_card()
        cards_layout.addWidget(card1, 1) #equal stretch factors
        
        #Card 2: Peak Force Display
        card2 = self.create_peak_force_card()
        cards_layout.addWidget(card2, 1)
        
        #Card 3: Rate analysis card
        card3 = self.create_rate_analysis_card()
        cards_layout.addWidget(card3, 1)
        
        layout.addLayout(cards_layout)

    #Acquisition control card
    def create_acquisition_control_card(self):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(165)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(8)

        #Card header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel("▶")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Acquisition Control")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)

        #Start stop buttons
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

        button_container = QWidget()
        button_container.setStyleSheet("background: transparent; border: none;")
        button_layout2 = QHBoxLayout(button_container)
        button_layout2.setSpacing(0)
        button_layout2.setContentsMargins(0, 0, 0, 0)
        button_layout2.addWidget(self.start_button)
        button_layout2.addWidget(self.stop_button)
        card_layout.addWidget(button_container)

        # Clear Data button
        clear_button = QPushButton("Clear Data")
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 2px;
                padding: 7px 12px;
                font-size: 12px;
                margin: 0px;
            }
        """)
        clear_button.clicked.connect(self.on_clear_data_clicked)
        card_layout.addWidget(clear_button)
        
        # Export CSV button
        export_button = QPushButton("Export CSV")
        export_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 2px;
                padding: 7px 12px;
                font-size: 12px;
                margin: 0px;
            }
        """)
        export_button.clicked.connect(self.on_export_csv_clicked)

        card_layout.addWidget(export_button)
        card_layout.addStretch(1)
        
        return card

    def create_peak_force_card(self):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(165)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(0)

        #Card header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel("↑")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Peak Torque")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)


        #Peak value display
        self.peak_value_label = QLabel("0.0 N·m")
        self.peak_value_label.setStyleSheet("color: #1A1A1A; font-size: 28px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(self.peak_value_label)

        #Subtitle
        subtitle_label = QLabel("Maximum torque detected")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        #Status indicator
        self.recording_status_label = QLabel("Stopped")
        self.recording_status_label.setStyleSheet("""
            QLabel {
                background-color: #1A1A1A;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        self.recording_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recording_status_label.setMaximumWidth(80)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.recording_status_label)

        card_layout.addStretch(1)

        return card

    #Empty placeholder card
    def create_empty_card(self):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(165)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(12)
        card_layout.addStretch(1)
        
        return card

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
        graph_layout.setContentsMargins(16, 16, 16, 8)
        graph_layout.setSpacing(12)
        
        #Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        title_label = QLabel("Torque vs Time")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        
        subtitle_label = QLabel("Real-time torque measurement display")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addStretch(1)
        
        graph_layout.addLayout(header_layout)
        
        #Create pyqtgraph plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#FAFAFA')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)

        #Set axis labels
        self.plot_widget.setLabel('bottom', '')
        self.plot_widget.setLabel('left', '')
        
        #Format tick labels
        self.plot_widget.getAxis('bottom').setStyle(tickTextOffset=5)
        self.plot_widget.getAxis('left').setStyle(tickTextOffset=5)

        self.plot_widget.getAxis('left').tickStrings = lambda values, scale, spacing: [f"{v:.1f}" for v in values]
        
        self.plot_widget.setLimits(xMin=0)
        
        #Disable mouse interaction (pan, zoom)
        self.plot_widget.setMouseEnabled(x=False, y=False)
        self.plot_widget.setMenuEnabled(False)
        
        #Create plot line
        self.line = self.plot_widget.plot([], [], pen=pg.mkPen(color='#2196F3', width=2))

        #Set initial ranges
        #self.plot_widget.setXRange(0, 10, padding=0)
        self.plot_widget.setYRange(0, 500, padding=0)
        QTimer.singleShot(0, lambda: self.update_time_ticks(10))    #Update time ticks after initial layout
        
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.plot_widget)
        graph_layout.addWidget(canvas_widget)
        
        layout.addWidget(graph_card)

    #Stats cards
    def create_stats_cards(self, layout):
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        #Card 1: Total data points
        card1 = QFrame()
        card1.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(16, 12, 16, 12)
        card1_layout.setSpacing(4)
        label1 = QLabel("Data Points:")
        label1.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        self.stats_data_points = QLabel("0")
        self.stats_data_points.setStyleSheet("color: #1A1A1A; font-size: 20px; font-weight: 600; border: none;")
        card1_layout.addWidget(label1)
        card1_layout.addWidget(self.stats_data_points)

        #Card 2: Total duration
        card2 = QFrame()
        card2.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(16, 12, 16, 12)
        card2_layout.setSpacing(4)
        label2 = QLabel("Duration:")
        label2.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        self.stats_duration = QLabel("0.0 s")
        self.stats_duration.setStyleSheet("color: #1A1A1A; font-size: 20px; font-weight: 600; border: none;")
        card2_layout.addWidget(label2)
        card2_layout.addWidget(self.stats_duration)

        #Card 3: Sampling rate (fixed for now)
        card3 = QFrame()
        card3.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(16, 12, 16, 12)
        card3_layout.setSpacing(4)
        label3 = QLabel("Sampling Rate:")
        label3.setStyleSheet("color: #666666; font-size: 11px; border: none;")
        self.stats_sample_rate = QLabel(f"{self.sample_rate} Hz")
        self.stats_sample_rate.setStyleSheet("color: #1A1A1A; font-size: 20px; font-weight: 600; border: none;")
        card3_layout.addWidget(label3)
        card3_layout.addWidget(self.stats_sample_rate)

        stats_layout.addWidget(card1, 1)
        stats_layout.addWidget(card2, 1)
        stats_layout.addWidget(card3, 1)
        layout.addLayout(stats_layout)

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
            self.raw_force_data.clear()
            self.data_point_count = 0
            self.acquisition_start_time = None

            #Reset peak value
            self.peak_value_label.setText("0.0 N·m")

            #Disable and clear rate analysis
            self.rate_start_input.setEnabled(False)
            self.rate_start_input.clear()
            self.rate_end_input.setEnabled(False)
            self.rate_end_input.clear()
            self.rate_value_label.setText("—")
            self.clear_rate_lines()

            #Update recording status
            self.recording_status_label.setText("Recording")
            self.recording_status_label.setStyleSheet("""
                QLabel {
                    background-color: #1A1A1A;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

            #Send start command
            self.x_axis_max = 1 #minimum 1 second display
            self.acquisition_timer.start(self.max_duration * 1000) #start timer for max duration
            self.send_data.emit("start")
            print("Acquisition started")
    
    #Stop clicked
    def on_stop_clicked(self):
        if self.is_acquiring:
            self.is_acquiring = False
            self.start_button.setChecked(False)
            self.stop_button.setChecked(True)
            self.update_button_styles()

            #Update recording status
            self.recording_status_label.setText("Stopped")
            self.recording_status_label.setStyleSheet("""
                QLabel {
                    background-color: #1A1A1A;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)

            self.acquisition_timer.stop()
            self.send_data.emit("stop")
            print("Acquisition stopped")
            print(f"Data points: {self.data_point_count}")

            #Enable rate analysis inputs
            self.rate_start_input.setEnabled(True)
            self.rate_end_input.setEnabled(True)
    
    #Clear data clicked
    def on_clear_data_clicked(self):
        if not self.is_acquiring:
            self.time_data.clear()
            self.force_data.clear()
            self.raw_force_data.clear()
            self.data_point_count = 0
            self.acquisition_start_time = None
            self.x_axis_max = 1
            self.peak_value_label.setText("0.0 N·m")
            self.line.setData([], [])
            #self.plot_widget.setXRange(0, 10, padding=0)
            self.plot_widget.setYRange(0, 500)
            self.update_time_ticks(10)
            self.stats_data_points.setText("0")
            self.stats_duration.setText("0.0 s")

            #Clear rate analysis
            self.rate_start_input.setEnabled(False)
            self.rate_start_input.clear()
            self.rate_end_input.setEnabled(False)
            self.rate_end_input.clear()
            self.rate_value_label.setText("—")
            self.clear_rate_lines()

            #Emit signal to clear filters
            self.clear_data_selected.emit()
    
    #Export CSV clicked
    def on_export_csv_clicked(self):
        if(len(self.force_data) == 0):
            print("No data to export")
            return
        
        #Save file dialog (in settings in future)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",       #Window title
            "lsmd_data.csv",       #Default file name
            "CSV Files (*.csv)"    #File filter
        )

        #If closed without selecting file, return
        if not file_path:
            return
        
        limb_m = self.get_limb_length_m()
        #DataFrame with time and torque values
        df = pd.DataFrame({
            "Time (s)": list(self.time_data),
            "Torque (N·m)": [round(f * limb_m, 2) for f in self.force_data]}
        )

        #Peak torque and RTD written to row 1 only — remaining rows left blank
        peak_col = [f"{self.peak_torque:.2f}"] + [""] * (len(self.time_data) - 1)
        rate_col  = [f"{self.rtd:.2f}" if self.rtd is not None else "—"] + [""] * (len(self.time_data) - 1)

        df["Peak Torque (N·m)"]            = peak_col
        df["Rate of Torque Dev (N·m/s)"]   = rate_col

        #Write dataframe to CSV
        df.to_csv(file_path, index=False)
        print(f"Data exported to {file_path}")
    
    #Update button styles based on acquisition state
    def update_button_styles(self):
        #Acquiring state
        if self.is_acquiring:
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #1A1A1A;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 7px 12px;
                    font-size: 12px;
                    margin: 0px;
                }
            """)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #666666;
                    border: 1px solid #E0E0E0;
                    border-radius: 2px;
                    padding: 7px 12px;
                    font-size: 12px;
                    margin: 0px;
                }
            """)
        #Not acquiring state
        else:
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #666666;
                    border: 1px solid #E0E0E0;
                    border-radius: 2px;
                    padding: 7px 12px;
                    font-size: 12px;
                    margin: 0px;
                }
            """)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #1A1A1A;
                    color: white;
                    border: none;
                    border-radius: 2px;
                    padding: 7px 12px;
                    font-size: 12px;
                    margin: 0px;
                }
            """)
    
    #Switch view button clicked
    def on_switch_view_clicked(self):
        self.switch_view.emit()

    def on_settings_clicked(self):
        self.navigate_to_settings.emit()

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
        
        #Convert bytes to string
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except:
                print(f"Could not decode data: {data}")
                return
        
        #Add to buffer
        self.data_buffer += data
        
        #Process complete lines
        while '\n' in self.data_buffer:
            line, self.data_buffer = self.data_buffer.split('\n', 1)
            line = line.strip()
            
            if not line:
                continue
            
            #Try to parse as float
            try:
                force_value = float(line)

                #Reject values outside of expected 10 bit range (0-1023)
                if force_value < 0 or force_value > 1023:
                    continue

                #Calculate time from sample count
                time_value = self.data_point_count / self.sample_rate

                #Apply piecewise calibration if available, otherwise pass raw ADC value
                if self.piecewise_cal and self.piecewise_cal.is_calibrated:
                    corrected_value = self.piecewise_cal.adc_to_newtons(force_value) - self.zero_offset
                else:
                    corrected_value = force_value - self.zero_offset

                self.time_data.append(time_value)
                self.force_data.append(corrected_value)
                self.raw_force_data.append(corrected_value)
                self.data_point_count += 1

                #Update plot every 60 points (~50ms at 1200 Hz)
                if self.data_point_count % 60 == 0:
                    self.update_plot()
                    
            except ValueError:
                print(f"Could not parse: {line}")
    
    #Acquisition timeout (10 seconds)
    def _on_acquisition_timeout(self):
        self.x_axis_max = self.max_duration
        self.on_stop_clicked()     #stop acquisition
        self.update_plot()         #update plot with final data
        
        
    def update_plot(self):
        if len(self.time_data) > 0:
            limb_m = self.get_limb_length_m()
            torque_data = [f * limb_m for f in self.force_data]
            self.line.setData(list(self.time_data), torque_data)

            #Auto-scale x-axis as data acquired, max 10 seconds
            max_time = max(self.time_data)
            if self.is_acquiring:
                self.x_axis_max = max(max_time, 1)
            #self.plot_widget.setXRange(0, self.x_axis_max, padding=0)
            self.update_time_ticks(self.x_axis_max)


            #Auto-scale y-axis
            if len(torque_data) > 0:
                min_torque = min(torque_data)
                max_torque = max(torque_data)
                margin = (max_torque - min_torque) * 0.1 if max_torque > min_torque else 10
                self.plot_widget.setYRange(max(0, min_torque - margin), max_torque + margin)

                #Update peak torque value
                self.peak_torque = max_torque
                self.peak_value_label.setText(f"{max_torque:.2f} N·m")

            self.stats_data_points.setText(str(self.data_point_count))
            self.stats_duration.setText(f"{max_time:.1f} s")

            #Send heartbeat to confirm updating
            #if self.is_acquiring:
            #    self.send_data.emit("stop")
    
    #Apply ordered list of filters to raw data, or revert if list is empty
    def apply_filter(self, filter_list):
        if len(self.raw_force_data) == 0:
            return

        # Start from raw data
        filtered = list(self.raw_force_data)

        # Apply each filter in order (notch, butterworth, moving average)
        for f in filter_list:
            filtered = f.apply(filtered)

        self.force_data.clear()
        self.force_data.extend(filtered)

        self.update_plot()

    #Update time ticks for x-axis to always displays 0 and 10 when timeout occurs
    def update_time_ticks(self, max_time):
        max_time = round(max_time, 1)
        
        if max_time <= 2:
            step = 0.5
        else:
            step = 1.0
        
        ticks = []
        time_value = step #skip 0 label
        #Add ticks for each step
        while time_value <= max_time:
            ticks.append((time_value, f"{time_value:.1f}"))
            time_value = round(time_value + step, 1)
        #Add final tick if not already at max time
        if ticks[-1][0] != max_time:
            ticks.append((max_time, f"{max_time:.1f}"))
        self.plot_widget.getAxis('bottom').setTicks([ticks])
        self.plot_widget.setXRange(0, max_time + 0.15, padding=0) #Padding so max time visible (label)

    #Rate analysis card
    def create_rate_analysis_card(self):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)

        card.setMinimumHeight(165)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(8)

        #Card header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel("↗")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Torque Rate Analysis")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)

        card_layout.addLayout(header_layout)

        #Start and End labels
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(12)

        start_label = QLabel("Start (s)")
        start_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        end_label = QLabel("End (s)")
        end_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")

        labels_layout.addWidget(start_label, 1)
        labels_layout.addWidget(end_label, 1)
        card_layout.addLayout(labels_layout)

        #Start and End inputs
        inputs_layout = QHBoxLayout()
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(12)

        self.rate_start_input = QLineEdit()
        self.rate_start_input.setPlaceholderText("")
        self.rate_start_input.setEnabled(False)
        self.rate_start_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1A1A1A;
            }
            QLineEdit:disabled {
                background-color: #EBEBEB;
                color: #999999;
            }
        """)
        self.rate_start_input.textChanged.connect(self.on_rate_input_changed)

        self.rate_end_input = QLineEdit()
        self.rate_end_input.setPlaceholderText("")
        self.rate_end_input.setEnabled(False)
        self.rate_end_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1A1A1A;
            }
            QLineEdit:disabled {
                background-color: #EBEBEB;
                color: #999999;
            }
        """)
        self.rate_end_input.textChanged.connect(self.on_rate_input_changed)

        inputs_layout.addWidget(self.rate_start_input, 1)
        inputs_layout.addWidget(self.rate_end_input, 1)
        card_layout.addLayout(inputs_layout)

        #Rate result
        rate_label = QLabel("Rate of Torque Development")
        rate_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(rate_label)

        #Default display
        self.rate_value_label = QLabel("—")
        self.rate_value_label.setStyleSheet("color: #1A1A1A; font-size: 20px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(self.rate_value_label)

        card_layout.addStretch(1)

        return card

    #Rate input changed
    def on_rate_input_changed(self):
        start_text = self.rate_start_input.text().strip()
        end_text = self.rate_end_input.text().strip()

        #When no input, default display
        if not start_text or not end_text:
            self.clear_rate_lines()
            self.rate_value_label.setText("—")
            return
        
        #Round to 1 decimal place
        try:
            start_val = round(float(start_text), 1)
            end_val = round(float(end_text), 1)
        except ValueError:
            self.clear_rate_lines()
            self.rate_value_label.setText("—")
            return

        #Clamp start to 0 min
        max_time = max(self.time_data) if len(self.time_data) > 0 else 0
        if start_val < 0:
            start_val = 0.0
            self.rate_start_input.setText(f"{start_val:.1f}")

        #Clamp end to max time recorded
        if end_val > max_time:
            end_val = round(max_time, 1)
            self.rate_end_input.setText(f"{end_val:.1f}")

        #Valid range, calculate and draw lines
        self.calculate_rate(start_val, end_val)
        self.draw_rate_lines(start_val, end_val)

    #Calculate average rate of force development
    def calculate_rate(self, start_time, end_time):

        #Reject if end is before start
        if end_time <= start_time:
            self.rtd = None
            self.rate_value_label.setText("—")
            return

        time_list = list(self.time_data)
        force_list = list(self.force_data)

        #Find closest indices for start and end
        start_index = min(range(len(time_list)), key=lambda i: abs(time_list[i] - start_time))
        end_index = min(range(len(time_list)), key=lambda i: abs(time_list[i] - end_time))

        #cannot be same
        if start_index == end_index:
            self.rtd = None
            self.rate_value_label.setText("—")
            return

        limb_m = self.get_limb_length_m()
        delta_torque = (force_list[end_index] - force_list[start_index]) * limb_m
        delta_time = time_list[end_index] - time_list[start_index]

        #cannot be zero
        if delta_time == 0:
            self.rtd = None
            self.rate_value_label.setText("—")
            return

        rate = delta_torque / delta_time
        self.rtd = rate  #store for export
        self.rate_value_label.setText(f"{rate:.2f} N·m/s")

    #Draw rate lines on plot
    def draw_rate_lines(self, start_time, end_time):
        #Remove existing lines
        self.clear_rate_lines()

        pen = pg.mkPen(color='#DAA520', width=1.5, style=Qt.PenStyle.DashLine)

        #Add vertical lines with labels
        self.rate_start_line = self.plot_widget.addLine(x=start_time, pen=pen, label='Start',
            labelOpts={'position': 0.85, 'color': '#DAA520', 'fill': '#FAFAFA'})
        self.rate_end_line = self.plot_widget.addLine(x=end_time, pen=pen, label='End',
            labelOpts={'position': 0.85, 'color': '#DAA520', 'fill': '#FAFAFA'})

    #Clear lines
    def clear_rate_lines(self):
        if hasattr(self, 'rate_start_line') and self.rate_start_line:
            self.plot_widget.removeItem(self.rate_start_line)
            self.rate_start_line = None
        if hasattr(self, 'rate_end_line') and self.rate_end_line:
            self.plot_widget.removeItem(self.rate_end_line)
            self.rate_end_line = None

    #Read limb length from settings, convert to meters, 0.5 m default
    def get_limb_length_m(self):
        if self.settings_window is None:
            return 0.50
        try:
            return float(self.settings_window.limb_length_input.text().strip()) / 100.0
        except (ValueError, AttributeError):
            return 0.50