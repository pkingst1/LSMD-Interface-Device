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
from utils.five_point_calibration import FivePointCalibration
from utils.piecewise_linear_calibration import PiecewiseLinearCalibration

class CalibrationWindow(QWidget):
 
    #Define signals
    navigate_to_dashboard = pyqtSignal()
    navigate_to_settings = pyqtSignal()
    disconnect_request = pyqtSignal()
    send_data = pyqtSignal(str)
    zero_calibration_complete = pyqtSignal(float)
    zero_status_updated = pyqtSignal(float, bool)
 
    def __init__(self, connection_type="usb", device_address=None, port_name=None, baud_rate=None, sample_rate=1200.0):
        super().__init__()
 
        #Store connection info for top bar display
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.sample_rate = sample_rate
        
        #Zero calibration data collection
        self.zero_cal = ZeroCalibration()
        self.zero_cal_buffer = []
        self.is_zero_collecting = False

        #Five point calibration data collection
        self.five_point_cal = FivePointCalibration()
        self.five_point_buffer = []
        self.is_five_point_collecting = False
        self.current_capture_index = 0          #Point 0-4 being captured
        self.point_boxes = []                    #Store references to each point's UI widgets

        self.piecewise_cal = PiecewiseLinearCalibration()
 
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
 
        #Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")

        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
 
        #Back to Settings link and page header
        self.create_page_header(content_layout)
 
        #Calibration status card with progress bar
        self.create_status_card(content_layout)
 
        #Two side-by-side calibration procedure cards
        self.create_calibration_cards(content_layout)

        #Calibration points card — hidden until "Start 5-Point Calibration" is clicked
        self.create_calibration_points_card(content_layout)

        #Calibration results card - hidden until all 5 points captured
        self.create_calibration_results_card(content_layout)
 
        #Push remaining space to bottom so cards stay at top
        content_layout.addStretch(1)
 
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
 
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

        #Info row
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)
        info_icon = QLabel("ⓘ")
        info_icon.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
        info_text = QLabel("Requires calibrated reference weights: 0, 25, 50, 75, 100N")
        info_text.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        info_row.addWidget(info_icon)
        info_row.addWidget(info_text)
        info_row.addStretch(1)
        card_layout.addLayout(info_row)

        #Start button — now connected
        self.five_point_start_button = QPushButton("▷  Start 5-Point Calibration")
        self.five_point_start_button.setFixedHeight(36)
        self.five_point_start_button.setStyleSheet("""
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
        self.five_point_start_button.clicked.connect(self.on_start_five_point_clicked)
        card_layout.addWidget(self.five_point_start_button)

        return card

    #Create calibration points card - hidden by default, appears when 5-point begins
    def create_calibration_points_card(self, layout):
        self.points_card = QFrame()
        self.points_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self.points_card.setVisible(False)

        card_layout = QVBoxLayout(self.points_card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(10)

        #Card header
        title_label = QLabel("Calibration Points")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("Progress through each calibration point")
        subtitle_label.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        #Horizontal row of 5 point boxes
        boxes_row = QHBoxLayout()
        boxes_row.setSpacing(12)

        self.point_boxes = []
        for i in range(5):
            box = self.create_point_box(i, f"Point {i + 1}, {i * 25}% Load (N)")
            boxes_row.addWidget(box)

        card_layout.addLayout(boxes_row)

        #Capture Reading button — centered below the boxes
        self.capture_reading_button = QPushButton("◎  Capture Reading")
        self.capture_reading_button.setFixedHeight(40)
        self.capture_reading_button.setFixedWidth(220)
        self.capture_reading_button.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.capture_reading_button.clicked.connect(self.on_capture_reading_clicked)
        card_layout.addWidget(self.capture_reading_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.points_card)

    #Create a single point box — percentage title, newton input, ADC result
    def create_point_box(self, index, percent_text):
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        box.setMinimumHeight(100)

        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 10, 10, 10)
        box_layout.setSpacing(4)
        box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        #Percentage title — bold, centered
        percent_label = QLabel(percent_text)
        percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        percent_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 600; background: transparent; border: none;")
        box_layout.addWidget(percent_label)

        #Newton input — small centered input field
        newton_input = QLineEdit()
        newton_input.setPlaceholderText("N")
        newton_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        newton_input.setMaximumWidth(80)
        newton_input.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 4px 6px;
                font-size: 12px;
                color: #666666;
            }
        """)
        input_container = QHBoxLayout()
        input_container.addStretch(1)
        input_container.addWidget(newton_input)
        input_container.addStretch(1)
        box_layout.addLayout(input_container)

        #ADC result label — hidden until captured
        adc_label = QLabel("")
        adc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        adc_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: 500; background: transparent; border: none;")
        adc_label.setVisible(False)
        box_layout.addWidget(adc_label)

        #Store references
        box_data = {
            'frame': box,
            'percent_label': percent_label,
            'newton_input': newton_input,
            'adc_label': adc_label,
            'captured': False
        }
        self.point_boxes.append(box_data)

        return box

    #Create the calibration results card - hidden until 5 points captured
    def create_calibration_results_card(self, layout):
        self.results_card = QFrame()
        self.results_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self.results_card.setVisible(False)

        card_layout = QVBoxLayout(self.results_card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(10)

        #Card header
        header_row = QHBoxLayout()
        header_row.setSpacing(6)
        icon_label = QLabel("✓")
        icon_label.setStyleSheet("color: #4CAF50; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Calibration Results")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_row.addWidget(icon_label)
        header_row.addWidget(title_label)
        header_row.addStretch(1)
        card_layout.addLayout(header_row)

        subtitle_label = QLabel("Review calibration accuracy and linearity")
        subtitle_label.setStyleSheet("color: #888888; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        #Horizontal row of 5 result boxes
        results_row = QHBoxLayout()
        results_row.setSpacing(12)

        self.result_boxes = []
        for i in range(5):
            result_box = self.create_result_box(i)
            results_row.addWidget(result_box)

        card_layout.addLayout(results_row)

        #Success message at the bottom
        self.results_message = QLabel("✓  Calibration completed successfully. Device is ready for accurate measurements.")
        self.results_message.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 10px 14px;
            }
        """)
        card_layout.addWidget(self.results_message)

        layout.addWidget(self.results_card)

    #Create a single result box — point title, interpolated value, error
    def create_result_box(self, index):
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
        """)

        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(10, 10, 10, 10)
        box_layout.setSpacing(4)

        #Point title
        title_label = QLabel(f"{index * 25}% Point")
        title_label.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        box_layout.addWidget(title_label)

        #Interpolated value — bold, placeholder for now
        value_label = QLabel("—")
        value_label.setStyleSheet("color: #1A1A1A; font-size: 16px; font-weight: 700; background: transparent; border: none;")
        box_layout.addWidget(value_label)

        #Error from real value — green
        error_label = QLabel("")
        error_label.setStyleSheet("color: #4CAF50; font-size: 11px; background: transparent; border: none;")
        box_layout.addWidget(error_label)

        #Store references
        result_data = {
            'frame': box,
            'title_label': title_label,
            'value_label': value_label,
            'error_label': error_label
        }
        self.result_boxes.append(result_data)

        return box
 
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
        
        #Stop five point collecting if in progress
        if self.is_five_point_collecting:
            self.is_five_point_collecting = False
            self.send_data.emit("stop")
            self.five_point_buffer = []
            self.capture_reading_button.setEnabled(True)
            self.capture_reading_button.setText("◎  Capture Reading")
        
        #Hide five point calibration points card
        self.points_card.setVisible(False)

        #Hide results card
        self.results_card.setVisible(False)

        #Restore zero button
        self.zero_start_button.setEnabled(True)

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

    #Receive incoming data during five point calibration
    def append_five_point_calibration_data(self, data):
        if not self.is_five_point_collecting:
            return

        #Convert bytes to string if needed
        if isinstance(data, bytes):
            try:
                data = data.decode('utf-8')
            except:
                return

        #Parse lines — same pattern as zero cal
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

                self.five_point_buffer.append(force_value)

                #Check if enough samples collected
                if len(self.five_point_buffer) >= self.five_point_cal.total_samples:
                    self.finish_five_point_capture()
                    return

            except ValueError:
                continue

    #Finish zero calibration, compute offset and update UI
    def finish_zero_calibration(self):
        #Stop collecting
        self.is_zero_collecting = False
        self.send_data.emit("stop")

        #Always apply full filter chain to calibration
        sample_rate = self.sample_rate
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

    #Start 5 point calibration, reveal points card, highlight first box
    def on_start_five_point_clicked(self):

        #Hide previous results
        self.results_card.setVisible(False)
        self.capture_reading_button.setVisible(True)
        self.capture_reading_button.setEnabled(True)
        self.capture_reading_button.setText("◎  Capture Reading")

        #Reset state
        self.five_point_cal.reset()
        self.current_capture_index = 0

        #Reset all boxes
        for box in self.point_boxes:
            box['captured'] = False
            box['newton_input'].setEnabled(True)
            box['newton_input'].clear()
            box['adc_label'].setVisible(False)
            box['adc_label'].setText("")
            box['frame'].setStyleSheet("""
                QFrame {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                }
            """)

        #Highlight first box as active
        self.point_boxes[0]['frame'].setStyleSheet("""
            QFrame {
                background-color: #F0FFF0;
                border: 2px solid #4CAF50;
                border-radius: 8px;
            }
        """)

        #Show the points card
        self.points_card.setVisible(True)

        #Update status card
        self.progress_bar.setValue(0)
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
        self.instruction_label.setText("Enter Newton value for Point 1, then click Capture Reading")
        self.cancel_button.setVisible(True)

    #Capture Reading button clicked — captures ADC for the current active point
    def on_capture_reading_clicked(self):
        index = self.current_capture_index
        box = self.point_boxes[index]

        #Validate newton input
        newton_text = box['newton_input'].text().strip()
        try:
            newton_value = float(newton_text)
        except ValueError:
            self.instruction_label.setText(f"Enter a valid Newton value for Point {index + 1}")
            return

        #Begin collecting
        self.current_capture_newton = newton_value
        self.five_point_buffer = []
        self.is_five_point_collecting = True

        #Update UI during capture
        self.capture_reading_button.setEnabled(False)
        self.capture_reading_button.setText("◎  Capturing...")
        self.instruction_label.setText(f"Capturing Point {index + 1}... Hold {newton_value}N steady")

        #Send start command
        self.send_data.emit("start")

    #Finish capturing a five point calibration point
    def finish_five_point_capture(self):
        self.is_five_point_collecting = False
        self.send_data.emit("stop")

        #Apply full filter chain
        sample_rate = self.sample_rate
        calibration_filters = [
            NotchFilter(sample_rate=sample_rate),
            ButterworthFilter(cutoff=100.0, sample_rate=sample_rate),
            MovingAverageFilter()
        ]
        adc_average = self.five_point_cal.compute_point_average(self.five_point_buffer, calibration_filters)

        if adc_average is None:
            self.instruction_label.setText("Capture failed — not enough samples")
            self.capture_reading_button.setEnabled(True)
            self.capture_reading_button.setText("◎  Capture Reading")
            return

        #Store the point
        index = self.current_capture_index
        newton_value = self.current_capture_newton
        self.five_point_cal.add_point(newton_value, adc_average)

        print(f"5-Point capture — Point {index + 1}: {newton_value}N → ADC {adc_average:.2f}")

        #Update captured box
        box = self.point_boxes[index]
        box['captured'] = True
        box['newton_input'].setEnabled(False)
        box['adc_label'].setText(f"✓ {adc_average:.1f}")
        box['adc_label'].setVisible(True)

        #Green fill on captured box
        box['frame'].setStyleSheet("""
            QFrame {
                background-color: #F0FFF0;
                border: 1px solid #4CAF50;
                border-radius: 8px;
            }
        """)

        #Update progress
        captured_count = self.five_point_cal.get_captured_count()
        self.progress_bar.setValue(captured_count * 20)

        #Advance or finish
        if index < 4:
            self.current_capture_index = index + 1

            #Highlight next box
            self.point_boxes[index + 1]['frame'].setStyleSheet("""
                QFrame {
                    background-color: #F0FFF0;
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                }
            """)

            self.instruction_label.setText(f"Point {index + 1} captured. Enter Newton value for Point {index + 2}")
            self.capture_reading_button.setEnabled(True)
            self.capture_reading_button.setText("◎  Capture Reading")
        else:
            #All done
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
            self.instruction_label.setText("5-Point calibration complete — all points captured")
            self.capture_reading_button.setVisible(False)
            self.cancel_button.setVisible(False)

            #Build the piecewise linear calibration from captured points
            self.piecewise_cal.load_points(self.five_point_cal.get_calibration_points())

            self.populate_results_card()

    #Populate the calibration results card with captured data and placeholder interpolation
    def populate_results_card(self):
        points = self.five_point_cal.get_calibration_points()
        results = self.piecewise_cal.get_interpolated_results(points)

        for i, result in enumerate(results):
            box = self.result_boxes[i]

            interpolated = result['newton_interpolated']
            error = result['error_absolute']
            error_percent = result['error_percent']

            box['value_label'].setText(f"{interpolated:.2f}N")

            if result['newton_entered'] != 0:
                box['error_label'].setText(f"Error: ±{error:.2f}N ({error_percent:.1f}%)")
            else:
                if error == 0:
                    box['error_label'].setText(f"Error: ±{error:.2f}N (0%)")
                else:
                    box['error_label'].setText(f"Error: ±{error:.2f}N")

        self.results_card.setVisible(True)