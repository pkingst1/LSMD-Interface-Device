"""
Toggle Switch - Reusable sliding toggle switch widget
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush

class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self.checked = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        #Track
        if self._checked:
            painter.setBrush(QBrush(QColor("#1A1A1A")))
        else:
            painter.setBrush(QBrush(QColor("#CCCCCC")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 3, 48, 20, 10, 10)

        #Knob
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        knob_x = 26 if self._checked else 2
        painter.drawEllipse(knob_x, 1, 24, 24)
        painter.end()