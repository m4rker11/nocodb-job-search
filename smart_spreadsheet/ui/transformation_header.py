from PyQt6.QtWidgets import QHeaderView, QStylePainter, QStyle, QStyleOptionButton
from PyQt6.QtCore import QRect, pyqtSignal, Qt
from PyQt6.QtGui import QColor

class TransformationHeader(QHeaderView):
    action_requested = pyqtSignal(int)  # Column index

    def __init__(self, get_column_role, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.get_column_role = get_column_role  # Store the role checker
        self.action_columns = set()

    def set_action_columns(self, columns):
        """Set which columns show action buttons"""
        self.action_columns = set(columns)
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        """Draw background and action button based on column role"""
        # Paint background first
        role = self.get_column_role(logicalIndex)  # Use passed function
        if role == 'input':
            painter.fillRect(rect, QColor(255, 255, 224, 127))  # Light yellow
        elif role == 'output':
            painter.fillRect(rect, QColor(173, 216, 230, 127))  # Light blue

        # Call parent to paint text
        super().paintSection(painter, rect, logicalIndex)

        # Draw action button if applicable
        if logicalIndex in self.action_columns:
            style = self.style()
            option = QStyleOptionButton()
            option.rect = QRect(rect.right() - 22, rect.top() + 2, 20, rect.height() - 4)
            style.drawControl(QStyle.ControlElement.CE_PushButton, option, painter)

    def mousePressEvent(self, event):
        """Handle clicks on action buttons"""
        col = self.logicalIndexAt(event.pos().x())
        if col in self.action_columns:
            self.action_requested.emit(col)
            return
        super().mousePressEvent(event)