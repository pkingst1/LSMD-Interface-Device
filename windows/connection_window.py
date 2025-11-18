"""
Connection Window - Device Connection Screen
User selects USB or Bluetooth connection
"""
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout,
                             QHBoxLayout, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal

#First Screen, device connection
class ConnectionWindow(QWidget):
    
    #Define signals
    usb_selected = pyqtSignal()
    bluetooth_selected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        #Initialize UI
        self.setWindowTitle("LSMD Data Interface")
        self.setMinimumSize(800, 500)

        #Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 0, 5, 30)

        #Top bar
        self.create_top_bar(main_layout)
        main_layout.addSpacing(10)
        main_layout.addStretch(2)

        #Central content
        central_widget = QWidget()
        central_widget.setMaximumWidth(650)
        central_layout = QVBoxLayout(central_widget)
        central_layout.setSpacing(40)

        #Add Header
        self.create_header(central_layout)
        
        #Connection cards
        self.create_connection_cards(central_layout)

        #Add footer
        self.create_footer(central_layout)

        #Center content horizontal
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        h_layout.addWidget(central_widget)
        h_layout.addStretch(1)

        main_layout.addLayout(h_layout)
        main_layout.addStretch(2)

    #Top bar
    def create_top_bar(self, layout):
        #Top bar with battery indicator and connection status
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

        #Connection indicator
        self.status_label = QLabel("Not Connected")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #DC3545;
                color: white;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        #self.status_label.setStyleSheet()

        top_bar.addWidget(self.status_label)

        layout.addLayout(top_bar)

    #Header
    def create_header(self, layout):
        #Header with title and subtitle
        header = QVBoxLayout()
        header.setSpacing(12)

        # Title
        title = QLabel("Device Connection")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 600;
                color: #FFFFFF;
            }
        """)

        # Subtitle
        subtitle = QLabel("Choose how you want to connect to your device")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #FFFFFF;
            }
        """)

        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

    #Connection cards
    def create_connection_cards(self, layout):
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)
        
        #USB Connection Card
        usb_card = self.create_card(
            icon="⚡",
            title="USB Connection",
            button_text="Connect via USB",
            is_primary=True
        )
        
        #Bluetooth Connection Card
        bluetooth_card = self.create_card(
            icon="ᚼᛒ",
            title="Bluetooth Connection",
            button_text="Connect via Bluetooth",
            is_primary=False
        )

        cards_layout.addWidget(usb_card)
        cards_layout.addWidget(bluetooth_card)

        layout.addLayout(cards_layout)
    
    #Cards
    def create_card(self, icon, title, button_text, is_primary=False):
        card = QFrame()
        card.setFixedSize(280, 240)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(24, 32, 24, 28)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 56px; color: #424242;")

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button = QPushButton(button_text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(44)

        if is_primary:
            #Black button
            button.clicked.connect(self.on_usb_clicked)
        else:
            #
            button.clicked.connect(self.on_bluetooth_clicked)
        
        card_layout.addWidget(icon_label)
        card_layout.addWidget(title_label)
        card_layout.addStretch(1)
        card_layout.addWidget(button)
        
        return card
    
    #Footer
    def create_footer(self, layout):
        footer = QLabel("Make sure your device is powered on and in pairing mode")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("""
            QLabel {
                font-size: 15px;
                color: #FFFFFF;
            }
        """)
        layout.addWidget(footer)

    #Signals for USB and Bluetooth selection
    #USB
    def on_usb_clicked(self):
        self.update_connection_status("USB")
        self.usb_selected.emit()

    #Bluetooth
    def on_bluetooth_clicked(self):
        self.update_connection_status("Bluetooth")
        self.bluetooth_selected.emit()

    #Update the connection status badge
    def update_connection_status(self, connection_type=None):
        if connection_type == "USB":
            self.status_label.setText("USB Connected")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #B2BEB5;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        
        elif connection_type == "Bluetooth":
            self.status_label.setText("Bluetooth Connected")
            self.status_label.setStyleSheet("""
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
            self.status_label.setText("Not Connected")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #DC3545;
                    color: white;
                    padding: 6px 14px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)