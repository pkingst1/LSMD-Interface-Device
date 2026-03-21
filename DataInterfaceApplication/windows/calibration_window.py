"""
Calibration window - Initiating and saving zero and five point calibration
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame, QComboBox, QCheckBox,
                             QScrollArea, QLineEdit, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from utils.toggle_switch import ToggleSwitch
from utils.notch_filter import NotchFilter
from utils.butterworth_filter import ButterworthFilter
from utils.moving_average_filter import MovingAverageFilter
from utils.zero_calibration import ZeroCalibration

class CalibrationWindow(QWidget):
 
    #Define signals
    navigate_to_dashboard = pyqtSignal()
    navigate_to_settings = pyqtSignal()
    disconnect_request = pyqtSignal()
    send_data = pyqtSignal(str)
    zero_calibration_complete = pyqtSignal(float)
    zero_status_updated = pyqtSignal(float, bool)
 
    def __init__(self, connection_type="usb", device_address=None, port_name=None, baud_rate=None):
        super().__init__()
 
        #Store connection info for top bar display
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate
        
        #Zero calibration data collection
        self.zero_cal = ZeroCalibration()
        self.zero_cal_buffer = []
        self.is_zero_collecting = False
 
        #Initialize the UI
        self.init_ui()
 
    #Build the full calibration window layout
    def init_ui(self):
        self.setWindowTitle("LSMD Data Interface - Calibration")
        self.setMinimumSize(1100, 700)
 
        #Main vertical layout for the entire window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 30)
        main_layout.setSpacing(0)
 
        #Build top bar rows (battery, connection status, nav ticker, disconnect)
        self.create_top_bar(main_layout)
 
        #Content area below top bar — same margins as settings scroll content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
 
        #Back to Settings link and page header
        self.create_page_header(content_layout)
 
        #Calibration status card with progress bar
        self.create_status_card(content_layout)
 
        #Two side-by-side calibration procedure cards
        self.create_calibration_cards(content_layout)
 
        #Push remaining space to bottom so cards stay at top
        content_layout.addStretch(1)
 
        main_layout.addWidget(content_widget)
 
    #Top bar, battery, navigation, connection, disconnect
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
        self.dashboard_tab.clicked.connect(self.on_dashboard_clicked)

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
 
    #Create the "Back to Settings" link and page title/subtitle
    def create_page_header(self, layout):
        #Title row: back button and title on same line
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(16)

        #Back to Settings clickable link
        back_button = QPushButton("← Back to Settings")
        back_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 12px;
                font-weight: 500;
                text-align: left;
                padding: 0px;
            }
            QPushButton:hover {
                color: #CCCCCC;
            }
        """)
        back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        back_button.clicked.connect(self.on_back_to_settings_clicked)

        #Page title and subtitle stacked vertically
        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title_label = QLabel("Device Calibration")
        title_label.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle_label = QLabel("Calibrate your force measurement device for accurate readings")
        subtitle_label.setStyleSheet("font-size: 14px; color: #666666;")

        title_block.addWidget(title_label)
        title_block.addWidget(subtitle_label)

        title_row.addWidget(back_button)
        title_row.addLayout(title_block)
        title_row.addStretch(1)
        layout.addLayout(title_row)
 
    #Create the calibration status card with progress bar
    def create_status_card(self, layout):
        status_card = QFrame()
        status_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
 
        card_layout = QVBoxLayout(status_card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(8)
 
        #Card header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
 
        icon_label = QLabel("◎")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
 
        title_label = QLabel("Calibration Status")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
 
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)
 
        #Progress row: "Progress" label on left, "Ready" badge on right
        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(0, 0, 0, 0)
 
        progress_label = QLabel("Progress")
        progress_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
 
        self.ready_badge = QLabel("Ready")
        self.ready_badge.setStyleSheet("""
            QLabel {
                background-color: #F0F0F0;
                color: #666666;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                border: 1px solid #E0E0E0;
            }
        """)
 
        progress_row.addWidget(progress_label)
        progress_row.addStretch(1)
        progress_row.addWidget(self.ready_badge)
        card_layout.addLayout(progress_row)
 
        #Progress bar — black bar indicating "Ready" state
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E8E8E8;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #1A1A1A;
                border-radius: 4px;
            }
        """)
        card_layout.addWidget(self.progress_bar)
 
        #Instruction text below the progress bar
        self.instruction_label = QLabel("Select a calibration procedure to begin")
        self.instruction_label.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        card_layout.addWidget(self.instruction_label)

        #Cancel button - hidden by default
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedHeight(32)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)
        card_layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignLeft)
 
        layout.addWidget(status_card)
 
    #Create the two side-by-side calibration procedure cards
    def create_calibration_cards(self, layout):
        #Horizontal layout for the two cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
 
        #Left card: Zero Calibration
        zero_card = self.create_zero_calibration_card()
        cards_row.addWidget(zero_card)
 
        #Right card: 5-Point Calibration
        five_card = self.create_five_point_calibration_card()
        cards_row.addWidget(five_card)
 
        layout.addLayout(cards_row)
 
    #Create the Zero Calibration procedure card
    def create_zero_calibration_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
 
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(6)
 
        #Card title
        title_label = QLabel("Zero Calibration")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title_label)
 
        #Card subtitle
        subtitle_label = QLabel("Remove measurement offset by setting zero reference point")
        subtitle_label.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)
 
        card_layout.addStretch(1)
 
        #Info/instruction row with info icon
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)
 
        info_icon = QLabel("ⓘ")
        info_icon.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
 
        info_text = QLabel("Ensure no force is applied to the device during zeroing")
        info_text.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
 
        info_row.addWidget(info_icon)
        info_row.addWidget(info_text)
        info_row.addStretch(1)
        card_layout.addLayout(info_row)
 
        #Start Zero Calibration button — dark filled style, no functionality
        self.zero_start_button = QPushButton("◎  Start Zero Calibration")
        self.zero_start_button.setFixedHeight(36)
        self.zero_start_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        self.zero_start_button.clicked.connect(self.on_zero_calibration_clicked)
        card_layout.addWidget(self.zero_start_button)
 
        return card
 
    #Create the 5-Point Calibration procedure card
    def create_five_point_calibration_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
 
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(6)
 
        #Card title
        title_label = QLabel("5-Point Calibration")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title_label)
 
        #Card subtitle
        subtitle_label = QLabel("Full range calibration using known reference weights")
        subtitle_label.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)
 
        card_layout.addStretch(1)
 
        #Info/instruction row with info icon
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)
 
        info_icon = QLabel("ⓘ")
        info_icon.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
 
        info_text = QLabel("Requires calibrated reference weights: 0, 20, 40, 60, 80, 100N")
        info_text.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
 
        info_row.addWidget(info_icon)
        info_row.addWidget(info_text)
        info_row.addStretch(1)
        card_layout.addLayout(info_row)
 
        #Start 5-Point Calibration button — outlined style, no functionality
        start_button = QPushButton("▷  Start 5-Point Calibration")
        start_button.setFixedHeight(36)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        card_layout.addWidget(start_button)
 
        return card
 
    #Handle "Back to Settings" click — emit signal to return to settings view
    def on_back_to_settings_clicked(self):
        self.navigate_to_settings.emit()
 
    #Handle Dashboard tab click — emit signal to navigate to dashboard
    def on_dashboard_clicked(self):
        self.navigate_to_dashboard.emit()
 
    #Handle Settings tab click — same as back to settings
    def on_settings_clicked(self):
        self.navigate_to_settings.emit()
 
    #Handle Disconnect button click — emit disconnect signal
    def on_disconnect_clicked(self):
        self.disconnect_request.emit()

    #Zero calibration button clicked — send start command and begin collecting data
    def on_zero_calibration_clicked(self):
        #Reset collection buffer
        self.zero_cal_buffer = []
        self.is_zero_collecting = True

        #Update progress bar to 50%
        self.progress_bar.setValue(50)

        #Update badge to "In Progress"
        self.ready_badge.setText("In Progress")
        self.ready_badge.setStyleSheet("""
            QLabel {
                background-color: #F0F0F0;
                color: #666666;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                border: 1px solid #E0E0E0;
            }
        """)

        #Update instruction text
        self.instruction_label.setText("Zeroing device... Please ensure no force is applied")

        #Update zero button to "Zeroing..." disabled state
        self.zero_start_button.setText("◎  Zeroing...")
        self.zero_start_button.setEnabled(False)
        self.zero_start_button.setStyleSheet("""
            QPushButton {
                background-color: #888888;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)

        #Show cancel button
        self.cancel_button.setVisible(True)

        #Send start command to microcontroller
        self.send_data.emit("start")

    #Cancel clicked — cancel zero calibration and reset to intial state
    def on_cancel_clicked(self):
        #Stop collecting if in progress
        if self.is_zero_collecting:
            self.is_zero_collecting = False
            self.send_data.emit("stop")
            self.zero_cal_buffer = []

        #Reset UI to initial state
        self.progress_bar.setValue(0)

        self.ready_badge.setText("Ready")
        self.ready_badge.setStyleSheet("""
            QLabel {
                background-color: #F0F0F0;
                color: #666666;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                border: 1px solid #E0E0E0;
            }
        """)

        self.instruction_label.setText("Select a calibration procedure to begin")

        self.cancel_button.setVisible(False)

        self.zero_start_button.setText("◎  Start Zero Calibration")
        self.zero_start_button.setEnabled(True)
        self.zero_start_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
    
    #Receive incoming data during zero calibration
    #Called by main when data arrives and calibration is collecting
    def append_zero_calibration_data(self, data):
        if not self.is_zero_collecting:
            return

        #Convert bytes to string if needed
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except:
                return

        #Parse lines from data
        lines = data.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            #Skip debug/status lines from microcontroller
            if line.startswith('>') or line.startswith('[') or line.startswith('=') or line.startswith('-'):
                continue

            try:
                force_value = float(line)

                #Reject values outside 10-bit ADC range
                if force_value < 0 or force_value > 1023:
                    continue

                self.zero_cal_buffer.append(force_value)

                #Print buffer progress every 100 samples for debugging
                #if len(self.zero_cal_buffer) % 100 == 0:
                #    print(f"Zero cal buffer: {len(self.zero_cal_buffer)} / {self.zero_cal.total_samples}")

                #Check if we have enough samples
                if len(self.zero_cal_buffer) >= self.zero_cal.total_samples:
                    self.finish_zero_calibration()
                    return

            except ValueError:
                continue

    #Finish zero calibration, compute offset and update UI
    def finish_zero_calibration(self):
        #Stop collecting
        self.is_zero_collecting = False
        self.send_data.emit("stop")

        #Always apply full filter chain to calibration
        sample_rate = 1200
        calibration_filters = [
            NotchFilter(sample_rate=sample_rate),
            ButterworthFilter(cutoff=100.0, sample_rate=sample_rate),
            MovingAverageFilter()
        ]
        offset = self.zero_cal.compute_zero_offset(self.zero_cal_buffer, calibration_filters)

        print(f"Zero calibration complete — offset: {offset:.2f}")

        #Emit the computed offset so main.py can apply to dashboard readings
        self.zero_calibration_complete.emit(offset)
        self.zero_status_updated.emit(offset, True)

        #Update UI to ready state
        self.progress_bar.setValue(100)

        self.ready_badge.setText("Complete")
        self.ready_badge.setStyleSheet("""
            QLabel {
                background-color: #1A1A1A;
                color: white;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                border: none;
            }
        """)

        self.instruction_label.setText(f"Calibration complete — Zero offset: {offset:.2f}")

        self.cancel_button.setVisible(False)

        self.zero_start_button.setText("◎  Start Zero Calibration")
        self.zero_start_button.setEnabled(True)
        self.zero_start_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 500;
            }
        """)