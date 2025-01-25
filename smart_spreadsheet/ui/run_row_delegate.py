from PyQt6.QtCore import pyqtSignal, QEvent, Qt
from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle
from PyQt6.QtGui import QPainter

class RunRowDelegate(QStyledItemDelegate):
    clicked = pyqtSignal(int)  # Emits row index when clicked

    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        if index.column() == 0:  # Assuming __Run_Row__ is the first column
            # Draw play icon
            icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
            rect = option.rect
            icon.paint(painter, rect, Qt.AlignmentFlag.AlignCenter)
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and index.column() == 0:
            self.clicked.emit(index.row())
            return True
        return super().editorEvent(event, model, option, index)