"""
Settings Window - Application and Device Settings
Preserves connection state between data acquisition window
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame, QComboBox, QCheckBox,
                             QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from utils.toggle_switch import ToggleSwitch

class SettingsWindow(QWidget):

    #Define signals
    navigate_to_dashboard = pyqtSignal()
    disconnect_request = pyqtSignal()
    filter_enabled = pyqtSignal(bool)

    def __init__(self, connection_type, device_address=None, port_name=None, baud_rate=None):
        super().__init__()
        self.connection_type = connection_type
        self.device_address = device_address
        self.port_name = port_name
        self.baud_rate = baud_rate

        self.init_ui()

    def init_ui(self):
        #Initialize UI
        self.setWindowTitle("LSMD Data Interface - Settings")
        self.setMinimumSize(1100, 700)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 30)
        main_layout.setSpacing(0)

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

        self.create_pager_header(content_layout)
        self.create_settings_cards(content_layout)
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

    def create_pager_header(self, layout):
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle = QLabel("Configure your device settings and application preferences")
        subtitle.setStyleSheet("font-size: 14px; color: #666666;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header_widget)

    #Settings cards
    def create_settings_cards(self, layout):
        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        #Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(16)

        #Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(16)

        #Card 1: Filtering (top right)
        card1 = QFrame()
        card1.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        card1.setMinimumHeight(200)

        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(16, 12, 16, 16)
        card1_layout.setSpacing(4)

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("▽")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Filtering")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card1_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Configure signal processing filters for data acquisition")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card1_layout.addWidget(subtitle_label)

        card1_layout.addSpacing(6)

        #Filter preset dropdown
        preset_label = QLabel("Filter Preset:")
        preset_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card1_layout.addWidget(preset_label)

        preset_dropdown = QComboBox()
        preset_dropdown.addItems(["None (Disabled)", "Enable All (Default)", "Custom"])
        preset_dropdown.setStyleSheet("""
            QComboBox {
                color: #1A1A1A;
                font-size: 12px;
                padding: 6px 10px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 6px 10px
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox:: QAbstractItemView {
                font-size: 12px;
                border: 1px solid #E0E0E0;
                selection-background-color: #F5F5F5;
                selection-color: #1A1A1A;
        """)

        card1_layout.addWidget(preset_dropdown)
        card1_layout.addSpacing(6)

        #Add filter rows
        card1_layout.addWidget(self.create_filter_rows("Notch Filter", "Attenuate specific frequency noise"))
        card1_layout.addWidget(self.create_filter_rows("Butterworth Filter", "Low-pass filter for signal smoothing"))
        card1_layout.addWidget(self.create_filter_rows("Moving Average Filter", "Smooth data using rolling average"))

        card1_layout.addStretch(1)

        #Card 3: Empty for now (middle left)
        card3 = QFrame()
        card3.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card3.setMinimumHeight(155)

        #Card 5: Empty for now (bottom left)
        card5 = QFrame()
        card5.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card5.setMinimumHeight(155)

        #Card2: empty for now (top right)
        card2 = QFrame()
        card2.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card2.setMinimumHeight(200)

        #Card4: empty for now (middle right)
        card4 = QFrame()
        card4.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card4.setMinimumHeight(155)

        #Card6: empty for now (middle right)
        card6 = QFrame()
        card6.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card6.setMinimumHeight(155)

        left_column.addWidget(card1)
        left_column.addWidget(card3)
        left_column.addWidget(card5)

        right_column.addWidget(card2)
        right_column.addWidget(card4)
        right_column.addWidget(card6)

        main_row.addLayout(left_column, 1)
        main_row.addLayout(right_column, 1)

        layout.addLayout(main_row)

    def on_dashboard_clicked(self):
        self.navigate_to_dashboard.emit()

    def on_settings_clicked(self):
        pass

    def on_disconnect_clicked(self):
        self.disconnect_request.emit()
    
    #Make filter rows function, takes name and subtitle of filter
    def create_filter_rows(self, name, subtitle):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent; border: none;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(8)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        text_layout.addWidget(name_label)
        text_layout.addWidget(sub_label)

        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                background-color: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background-color: #1A1A1A;
                border: 1px solid #1A1A1A;
            }
        """)

        row_layout.addLayout(text_layout)
        row_layout.addStretch(1)
        row_layout.addWidget(checkbox)
        return row_widget