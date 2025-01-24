from PyQt6.QtWidgets import QHeaderView, QStylePainter, QStyle, QStyleOptionButton
from PyQt6.QtCore import QRect, pyqtSignal, Qt

class TransformationHeader(QHeaderView):
    action_requested = pyqtSignal(int)  # Column index
    
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.action_columns = set()
        
    def set_action_columns(self, columns):
        """Set which columns show action buttons"""
        self.action_columns = set(columns)
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        """Override to draw action indicators"""
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex in self.action_columns:
            # Draw styled button indicator
            style = self.style()
            option = QStyleOptionButton()
            option.rect = QRect(rect.right() - 22, rect.top() + 2, 20, rect.height() - 4)
            style.drawControl(QStyle.ControlElement.CE_PushButton, option, painter)

    def mousePressEvent(self, event):
        """Handle click events on action areas"""
        col = self.logicalIndexAt(event.pos().x())
        if col in self.action_columns:
            self.action_requested.emit(col)
            return
        super().mousePressEvent(event)