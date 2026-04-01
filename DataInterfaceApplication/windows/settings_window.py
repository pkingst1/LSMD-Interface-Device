"""
Settings Window - Application and Device Settings
Preserves connection state between data acquisition window
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame, QComboBox, QCheckBox,
                             QScrollArea, QLineEdit, QProgressBar, QGridLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from utils.toggle_switch import ToggleSwitch
from utils.notch_filter import NotchFilter
from utils.butterworth_filter import ButterworthFilter
from utils.moving_average_filter import MovingAverageFilter

class SettingsWindow(QWidget):

    #Define signals
    navigate_to_dashboard = pyqtSignal()
    disconnect_request = pyqtSignal()
    filter_settings_changed = pyqtSignal()
    navigate_to_calibration = pyqtSignal()
    auto_reconnect_changed = pyqtSignal(bool)
    auto_turn_off_changed = pyqtSignal(bool, int)  #enabled, minutes
    

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

    #Settings cards — grid layout ensures row pairs share the same height
    def create_settings_cards(self, layout):
        grid = QGridLayout()
        grid.setSpacing(16)

        #Card 1: Filtering (top left)
        card1 = self.create_filter_settings_card()

        #Card 2: Calibration card (top right)
        card2 = self.create_calibration_card()

        #Card 3: Measurement settings card (bottom left)
        card3 = self.create_measurement_settings_card()

        #Card 4: Device settings (bottom right)
        card4 = self.create_device_settings_card()

        #Card 5: Empty for now (row 3 left)
        card5 = QFrame()
        card5.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)

        #Card 6: Empty for now (row 3 right)
        card6 = QFrame()
        card6.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #1A1A1A;
                border-radius: 8px;
            }
        """)

        #Grid: row, col — cards in the same row share height automatically
        grid.addWidget(card1, 0, 0)  #Row 0, left
        grid.addWidget(card2, 0, 1)  #Row 0, right
        grid.addWidget(card3, 1, 0)  #Row 1, left
        grid.addWidget(card4, 1, 1)  #Row 1, right
        grid.addWidget(card5, 2, 0)  #Row 2, left
        grid.addWidget(card6, 2, 1)  #Row 2, right

        #Equal column stretch so both columns share width evenly
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        layout.addLayout(grid)

    def on_dashboard_clicked(self):
        self.navigate_to_dashboard.emit()

    def on_settings_clicked(self):
        pass

    def on_disconnect_clicked(self):
        self.disconnect_request.emit()
    
    #Make filter rows function, takes name and subtitle of filter, default not expandable (butterworth)
    def create_filter_rows(self, name, subtitle, is_expandable=False, param_label=None):
        input_box = None

        #Outer container
        outer_container = QWidget()
        outer_container.setStyleSheet("background: transparent; border: none;")
        outer_container_layout = QVBoxLayout(outer_container)
        outer_container_layout.setContentsMargins(0, 0, 0, 0)
        outer_container_layout.setSpacing(2)

        #Main row: name, title, checkbox
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
        outer_container_layout.addWidget(row_widget)

        if is_expandable and param_label:
            #Expanding portion to main row
            label = QLabel(param_label)
            label.setStyleSheet("color: #1A1A1A; font-size: 11px; background: transparent; border: none;")
            label.setVisible(False)

            input_box = QLineEdit()
            input_box.setMinimumWidth(10)
            input_box.setPlaceholderText("100")
            input_box.setStyleSheet("""
                QLineEdit {
                    background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                    padding: 6px 10px;
                    font-size: 11px;
                    color: #1A1A1A;
                }
            """)
            input_box.setVisible(False)

            #Insert before checkbox in main row
            row_layout.insertWidget(2, label)
            row_layout.insertWidget(3, input_box)

            #Checkbox toggles param row visibility
            checkbox.stateChanged.connect(label.setVisible)
            checkbox.stateChanged.connect(input_box.setVisible)

        outer_container.checkbox = checkbox #Store checkbox reference

        #Store input box reference
        outer_container.input_box = input_box if (is_expandable and param_label) else None
        outer_container.param_label = label if (is_expandable and param_label) else None

        return outer_container


    #Update filter preset dropdown
    def update_filter_preset_dropdown(self):
        #Get current filter settings
        notch_enabled = self.notch_row.checkbox.isChecked()
        butterworth_enabled = self.butterworth_row.checkbox.isChecked()
        moving_average_enabled = self.moving_average_row.checkbox.isChecked()

        #Cutoff custom if user input differs from default
        cutoff_text = self.butterworth_row.input_box.text().strip()
        cutoff_changed = cutoff_text not in ("", "100")

        #Set dropdown based on current settings
        all_on = notch_enabled and butterworth_enabled and moving_average_enabled
        all_off = not notch_enabled and not butterworth_enabled and not moving_average_enabled

        self.preset_dropdown.blockSignals(True)
        if all_on and not cutoff_changed:
            self.preset_dropdown.setCurrentIndex(1) #Enable All (Default)
        elif all_off and not cutoff_changed:
            self.preset_dropdown.setCurrentIndex(0) #None (Disabled)
        else:
            self.preset_dropdown.setCurrentIndex(2) #Custom
        self.preset_dropdown.blockSignals(False)

    #Filter preset changes
    def on_filter_preset_changed(self, index):
        enable = (index == 1)
        is_custom = (index == 2)
        #Block signals so setting doesn't trigger filter preset update
        for row in (self.notch_row, self.butterworth_row, self.moving_average_row):
            row.checkbox.blockSignals(True)
        self.butterworth_row.input_box.blockSignals(True)
        self.notch_row.checkbox.setChecked(enable)
        self.butterworth_row.checkbox.setChecked(enable)
        self.moving_average_row.checkbox.setChecked(enable)
        if not is_custom:
            self.butterworth_row.input_box.clear()
            self.butterworth_row.input_box.setVisible(False)
            self.butterworth_row.param_label.setVisible(False)
        #Unblock signals
        for row in (self.notch_row, self.butterworth_row, self.moving_average_row):
            row.checkbox.blockSignals(False)
        self.butterworth_row.input_box.blockSignals(False)
        self.filter_settings_changed.emit() #Apply new filter settings

    #Filter state changes
    #Emit signal on any filter state change
    def on_filter_changed(self):
        self.filter_settings_changed.emit()

    #Returns ordered list of active filters based on current settings
    def get_active_filters(self, sample_rate):
        filters = []
        #Order: Notch, Butterworth, Moving Average
        if self.notch_row.checkbox.isChecked():
            filters.append(NotchFilter(sample_rate=sample_rate))
        
        if self.butterworth_row.checkbox.isChecked():
            cutoff_text = self.butterworth_row.input_box.text().strip()
            try:
                cutoff = float(cutoff_text) if cutoff_text else 100.0
            except ValueError:
                cutoff = 100.0
            filters.append(ButterworthFilter(cutoff=cutoff, sample_rate=sample_rate))

        if self.moving_average_row.checkbox.isChecked():
            filters.append(MovingAverageFilter())

        return filters
    
    #Filter settings card
    def create_filter_settings_card(self):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        card.setMinimumHeight(250)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(4)

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("▽")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Filtering")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Configure signal processing filters for data acquisition")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        card_layout.addSpacing(6)

        #Filter preset dropdown
        preset_label = QLabel("Filter Preset:")
        preset_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(preset_label)

        preset_dropdown = QComboBox()
        preset_dropdown.addItems(["None (Disabled)", "Enable All (Default)", "Custom"])
        preset_dropdown.setStyleSheet("""
            QComboBox {
                color: #1A1A1A;
                font-size: 12px;
                padding: 6px 10px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                font-size: 12px;
                border: 1px solid #E0E0E0;
                selection-background-color: #F5F5F5;
                selection-color: #1A1A1A;
            }
        """)

        card_layout.addWidget(preset_dropdown)
        self.preset_dropdown = preset_dropdown
        preset_dropdown.currentIndexChanged.connect(self.on_filter_preset_changed)
        card_layout.addSpacing(6)

        #Store checkbox references, create rows
        self.notch_row = self.create_filter_rows("Notch Filter", "Attenuate specific frequency noise")
        self.butterworth_row = self.create_filter_rows(
            "Butterworth Filter", 
            "Low-pass filter for signal smoothing",
            is_expandable=True, 
            param_label="Cutoff (Hz):")
        self.moving_average_row = self.create_filter_rows("Moving Average Filter", "Smooth data using rolling average")

        card_layout.addWidget(self.notch_row)
        card_layout.addWidget(self.butterworth_row)
        card_layout.addWidget(self.moving_average_row)

        #Update dropdown change settings
        self.notch_row.checkbox.stateChanged.connect(self.update_filter_preset_dropdown)
        self.butterworth_row.checkbox.stateChanged.connect(self.update_filter_preset_dropdown)
        self.moving_average_row.checkbox.stateChanged.connect(self.update_filter_preset_dropdown)
        self.butterworth_row.input_box.textChanged.connect(self.update_filter_preset_dropdown)

        #Connect filter state changes
        self.notch_row.checkbox.stateChanged.connect(self.on_filter_changed)
        self.butterworth_row.checkbox.stateChanged.connect(self.on_filter_changed)
        self.moving_average_row.checkbox.stateChanged.connect(self.on_filter_changed)
        self.butterworth_row.input_box.textChanged.connect(self.on_filter_changed)

        card_layout.addStretch(1)

        return card

    #Create 3rd card: measurement settings
    def create_measurement_settings_card(self):
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

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("◎")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Measurement Settings")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Configure measurement parameters for torque calculations")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        #Limb length input
        limb_label = QLabel("Limb Length")
        limb_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(limb_label)

        limb_row = QHBoxLayout()
        limb_row.setContentsMargins(0, 0, 0, 0)
        limb_row.setSpacing(8)

        self.limb_length_input = QLineEdit("50")
        self.limb_length_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1A1A1A;
            }
        """)
        self.limb_length_input.editingFinished.connect(self.on_limb_length_changed)

        limb_unit = QComboBox()
        limb_unit.addItem("cm")
        limb_unit.setEnabled(False)
        limb_unit.setStyleSheet("""
            QComboBox {
                color: #1A1A1A;
                font-size: 12px;
                padding: 6px 10px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        limb_unit.setMinimumWidth(70)

        limb_row.addWidget(self.limb_length_input)
        limb_row.addWidget(limb_unit)
        card_layout.addLayout(limb_row)

        limb_desc = QLabel("Distance from joint center to force application point")
        limb_desc.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        card_layout.addWidget(limb_desc)

        # Force Units
        force_label = QLabel("Force Units")
        force_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(force_label)

        force_dropdown = QComboBox()
        force_dropdown.addItem("Newtons (N) (Fixed)")
        force_dropdown.setEnabled(False)
        force_dropdown.setStyleSheet("""
            QComboBox {
                color: #666666;
                font-size: 12px;
                padding: 6px 10px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        card_layout.addWidget(force_dropdown)

        card_layout.addSpacing(6)

        # Torque Units
        torque_label = QLabel("Torque Units")
        torque_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(torque_label)

        torque_dropdown = QComboBox()
        torque_dropdown.addItem("Newton-meters (N·m) (Fixed)")
        torque_dropdown.setEnabled(False)
        torque_dropdown.setStyleSheet("""
            QComboBox {
                color: #666666;
                font-size: 12px;
                padding: 6px 10px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        card_layout.addWidget(torque_dropdown)

        card_layout.addStretch(1)

        return card
    
    #Limb length changed
    def on_limb_length_changed(self):
        text = self.limb_length_input.text().strip()
        try:
            value = float(text)
            if value <= 0:
                raise ValueError
        except ValueError:
            self.limb_length_input.setText("50")

    #Calibration card
    def create_calibration_card(self):
        card = QFrame()
        card.setStyleSheet("""
        QFrame {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
        }
        """)
        card.setMinimumHeight(250)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(4)

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("⊕")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Device Calibration")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Calibrate and maintain measurement accuracy")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        card_layout.addSpacing(6)

        #Zero calibration status
        zero_container = QVBoxLayout()
        zero_container.setSpacing(1)
        zero_label = QLabel("Zero Calibration Status")
        zero_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        zero_container.addWidget(zero_label)

        zero_status_layout = QHBoxLayout()
        zero_status_layout.setContentsMargins(0, 0, 0, 0)
        zero_status_layout.setSpacing(4)
        self.zero_dot = QLabel("●")
        self.zero_dot.setStyleSheet("color: #DAA520; font-size: 10px; background: transparent; border: none;")
        self.zero_text = QLabel("Required every session")
        self.zero_text.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        zero_status_layout.addWidget(self.zero_dot)
        zero_status_layout.addWidget(self.zero_text)
        zero_status_layout.addStretch(1)
        zero_container.addLayout(zero_status_layout)
        card_layout.addLayout(zero_container)

        #5-point calibration status
        five_container = QVBoxLayout()
        five_container.setSpacing(1)
        five_label = QLabel("5-Point Calibration")
        five_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        five_container.addWidget(five_label)

        five_status_layout = QHBoxLayout()
        five_status_layout.setContentsMargins(0, 0, 0, 0)
        five_status_layout.setSpacing(4)
        self.five_dot = QLabel("●")
        self.five_dot.setStyleSheet("color: #DAA520; font-size: 10px; background: transparent; border: none;")
        self.five_text = QLabel("Not calibrated")
        self.five_text.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        five_status_layout.addWidget(self.five_dot)
        five_status_layout.addWidget(self.five_text)
        five_status_layout.addStretch(1)
        five_container.addLayout(five_status_layout)
        card_layout.addLayout(five_container)

        #Recommended frequency
        frequency_label = QLabel("Recommended Frequency: Every 6 months")
        frequency_label.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        card_layout.addWidget(frequency_label)

        card_layout.addStretch(1)

        #Open calibration panel button
        calibration_button = QPushButton("Open Calibration Panel")
        calibration_button.setStyleSheet("""
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
        #On calibraton button click, navigate to calibration window
        calibration_button.clicked.connect(self.on_calibration_clicked)
        card_layout.addWidget(calibration_button)

        return card

    #Clear filters
    def reset_filters(self):
        self.preset_dropdown.setCurrentIndex(0)

    #Device settings card
    def create_device_settings_card(self):
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

        #Card header
        header_layout = QHBoxLayout()
        icon_label = QLabel("⚙")
        icon_label.setStyleSheet("color: #1A1A1A; font-size: 14px; background: transparent; border: none;")
        title_label = QLabel("Device Settings")
        title_label.setStyleSheet("color: #1A1A1A; font-size: 14px; font-weight: 600; background: transparent; border: none;")
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        card_layout.addLayout(header_layout)

        #Subtitle
        subtitle_label = QLabel("Configure device-specific parameters")
        subtitle_label.setStyleSheet("color: #666666; font-size: 12px; background: transparent; border: none;")
        card_layout.addWidget(subtitle_label)

        #Sampling rate (fixed input)
        rate_label = QLabel("Sampling Rate")
        rate_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(rate_label)

        rate_input = QLineEdit("1200 Hz (Fixed)")
        rate_input.setEnabled(False)
        rate_input.setStyleSheet("""
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
        card_layout.addWidget(rate_input)

        rate_description = QLabel("High-frequency sampling for accurate force measurements")
        rate_description.setStyleSheet("color: #666666; font-size: 11px; background: transparent; border: none;")
        card_layout.addWidget(rate_description)

        #Connection timeout
        timeout_label = QLabel("Connection Timeout (seconds)")
        timeout_label.setStyleSheet("color: #1A1A1A; font-size: 12px; font-weight: 500; background: transparent; border: none;")
        card_layout.addWidget(timeout_label)

        timeout_input = QLineEdit("30")
        timeout_input.setEnabled(False)
        timeout_input.setStyleSheet("""
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
        card_layout.addWidget(timeout_input)

        #Auto turn off: toggle switch with mins inactivity input
        auto_off_row = QWidget()
        auto_off_row.setStyleSheet("background: transparent; border: none;")
        auto_off_layout = QHBoxLayout(auto_off_row)
        auto_off_layout.setContentsMargins(0, 4, 0, 0)
        auto_off_layout.setSpacing(8)

        auto_off_text_layout = QVBoxLayout()
        auto_off_text_layout.setSpacing(1)
        auto_off_name = QLabel("Auto Turn-Off")
        auto_off_name.setStyleSheet("""
            color: #1A1A1A; 
            font-size: 12px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
        """)
        auto_off_sub = QLabel("Automatically turn off device after inactivity")
        auto_off_sub.setStyleSheet("color: #888888; font-size: 11px; background: transparent; border: none;")
        auto_off_text_layout.addWidget(auto_off_name)
        auto_off_text_layout.addWidget(auto_off_sub)
 
        self.auto_off_toggle = ToggleSwitch()
        self.auto_off_toggle.setChecked(False)
        auto_off_layout.addLayout(auto_off_text_layout)
        auto_off_layout.addStretch(1)
        auto_off_layout.addWidget(self.auto_off_toggle)
        card_layout.addWidget(auto_off_row)

        #Mins of inactivity input (visible when auto turn off enabled)
        self.inactivity_label = QLabel("Minutes of inactivity")
        self.inactivity_label.setStyleSheet("""
            color: #1A1A1A; 
            font-size: 12px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
         """)
        self.inactivity_label.setVisible(False)
        card_layout.addWidget(self.inactivity_label)
 
        self.inactivity_input = QLineEdit("5")
        self.inactivity_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                padding: 6px 10px;
                font-size: 12px;
                color: #1A1A1A;
            }
        """)
        self.inactivity_input.setVisible(False)
        card_layout.addWidget(self.inactivity_input)

        self.inactivity_input.textChanged.connect(self._on_inactivity_input_changed)

        #Toggle controls inactivity input visibility
        self.auto_off_toggle.toggled.connect(self.on_auto_off_toggled)

        #Auto reconnect toggle
        auto_reconnect_row = QWidget()
        auto_reconnect_row.setStyleSheet("background: transparent; border: none;")
        auto_reconnect_layout = QHBoxLayout(auto_reconnect_row)
        auto_reconnect_layout.setContentsMargins(0, 4, 0, 0)
        auto_reconnect_layout.setSpacing(8)
 
        auto_reconnect_text_layout = QVBoxLayout()
        auto_reconnect_text_layout.setSpacing(1)
        auto_reconnect_name = QLabel("Auto-reconnect")
        auto_reconnect_name.setStyleSheet("""
            color: #1A1A1A; 
            font-size: 12px; 
            font-weight: 500; 
            background: transparent; 
            border: none;
            """)
        auto_reconnect_sub = QLabel("Automatically reconnect if connection is lost")
        auto_reconnect_sub.setStyleSheet("""
            color: #888888; 
            font-size: 11px; 
            background: transparent; 
            border: none;
        """)
        auto_reconnect_text_layout.addWidget(auto_reconnect_name)
        auto_reconnect_text_layout.addWidget(auto_reconnect_sub)
 
        self.auto_reconnect_toggle = ToggleSwitch()
        self.auto_reconnect_toggle.setChecked(False) #off by default
        self.auto_reconnect_toggle.toggled.connect(self.auto_reconnect_changed.emit)
 
        auto_reconnect_layout.addLayout(auto_reconnect_text_layout)
        auto_reconnect_layout.addStretch(1)
        auto_reconnect_layout.addWidget(self.auto_reconnect_toggle)
        card_layout.addWidget(auto_reconnect_row)

        card_layout.addStretch(1)
        
        return card

    #Auto turn-off toggle handler — show/hide minutes of inactivity input
    def on_auto_off_toggled(self, checked):
        self.inactivity_label.setVisible(checked)
        self.inactivity_input.setVisible(checked)
        #Emit current state and minutes value to main.py
        try:
            minutes = int(self.inactivity_input.text().strip())
        except ValueError:
            minutes = 5
        self.auto_turn_off_changed.emit(checked, minutes)

    #On calibration button click, navigate to calibration window
    def on_calibration_clicked(self):
        self.navigate_to_calibration.emit()

    #Update zero calibration status display
    def update_zero_status(self, offset, is_calibrated):
        if is_calibrated:
            self.zero_dot.setStyleSheet("color: #4CAF50; font-size: 10px; background: transparent; border: none;")
            self.zero_text.setText(f"Offset: {offset:.2f}")
        else:
            self.zero_dot.setStyleSheet("color: #DAA520; font-size: 10px; background: transparent; border: none;")
            self.zero_text.setText("Every session placeholder")

    #Update 5-point calibration date display
    def update_five_point_status(self, calibration_date):
        from datetime import date
        days_elapsed = (date.today() - calibration_date).days
        date_str = calibration_date.isoformat()  #eg "2026-04-01"

        self.five_text.setText(f"Last calibration: {date_str}")

        #Red if over 180 days, green otherwise
        if days_elapsed > 180:
            self.five_dot.setStyleSheet("color: #DC3545; font-size: 10px; background: transparent; border: none;")
        else:
            self.five_dot.setStyleSheet("color: #4CAF50; font-size: 10px; background: transparent; border: none;")

    #Inactivity input text changed handler
    def _on_inactivity_input_changed(self):
        if self.auto_off_toggle.isChecked():
            try:
                minutes = int(self.inactivity_input.text().strip())
            except ValueError:
                return
            self.auto_turn_off_changed.emit(True, minutes)