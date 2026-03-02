"""
Settings Window - Application and Device Settings
Preserves connection state between data acquisition window
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame)
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
        main_layout.setContentsMargins(5, 0, 5, 30)
        main_layout.setSpacing(15)

        self.create_top_bar(main_layout)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        self.create_pager_header(content_layout)
        self.create_settings_cards(content_layout)

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

        #Navigation ticker (Dashboard - Settings)
        navigation_widget = QWidget()
        navigation_layout = QHBoxLayout(navigation_widget)
        navigation_layout.setContentsMargins(0, 0, 0, 0)
        navigation_layout.setSpacing(0)

        self.dashboard_tab= QPushButton("Dashboard")
        self.dashboard_tab.setFixedWidth(32)
        self.dashboard_tab.setMinimumWidth(100)
        self.dashboard_tab.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: 1px solid #E0E0E0;
                border-radius: 6px 0px 0px 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        self.dashboard_tab.clicked.connect(self.on_dashboard_clicked)

        self.settings_tab = QPushButton("Settings")
        self.settings_tab.setFixedWidth(32)
        self.settings_tab.setMinimumWidth(100)
        self.settings_tab.setStyleSheet("""
            QPushButton {
                background-color: #1A1A1A;
                color: white;
                border: 1px solid #1A1A1A;
                border-radius: 0px 6px 6px 0px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        
        navigation_layout.addWidget(self.dashboard_tab)
        navigation_layout.addWidget(self.settings_tab)

        top_bar.addWidget(navigation_widget)
        top_bar.addStretch(1)

        #Right side: connection indicator and disconnect
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

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

    def create_pager_header(self, layout):
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")

        subtitle = QLabel("Configure your device settings and application preferences")
        subtitle.setStyleSheet("font-size: 14px; color: #666666;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

    #Settings cards
    def create_settings_cards(self, layout):
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(16)

        #Card 1: Filtering
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
        card1_layout.setContentsMargins(16, 16, 16, 16)
        card1_layout.setSpacing(12)

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("⚙")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Filtering")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card1_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Configure signal filtering")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card1_layout.addWidget(subtitle_label)

        # Enable Filters row
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 4, 0, 4)

        filter_text_layout = QVBoxLayout()
        filter_text_layout.setSpacing(2)

        filter_label = QLabel("Enable Filters")
        filter_label.setStyleSheet("color: #1A1A1A; font-size: 13px; font-weight: 500; background: transparent; border: none;")
        filter_sublabel = QLabel("Apply filter to data")
        filter_sublabel.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")

        filter_text_layout.addWidget(filter_label)
        filter_text_layout.addWidget(filter_sublabel)

        self.filter_toggle = ToggleSwitch()
        self.filter_toggle.setChecked(False)
        self.filter_toggle.toggled.connect(self.on_filter_toggled)

        filter_row.addLayout(filter_text_layout)
        filter_row.addStretch(1)
        filter_row.addWidget(self.filter_toggle)

        card1_layout.addLayout(filter_row)
        card1_layout.addStretch(1)

        #Card2: empty for now
        card2 = QFrame()
        card2.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)
        card2.setMinimumHeight(200)

        cards_layout.addWidget(card1, 1)
        cards_layout.addWidget(card2, 1)

        layout.addLayout(cards_layout)

    #On filter toggle
    def on_filter_toggled(self, enabled):
        self.filter_enabled.emit(enabled)

    def on_dashboard_clicked(self):
        self.navigate_to_dashboard.emit()

    def on_settings_clicked(self):
        pass

    def on_disconnect_clicked(self):
        self.disconnect_request.emit()