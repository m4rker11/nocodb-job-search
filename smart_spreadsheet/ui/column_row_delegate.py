from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QColor
class ColumnRoleDelegate(QStyledItemDelegate):
    def __init__(self, get_column_role, parent=None):
        super().__init__(parent)
        self.get_column_role = get_column_role

    def paint(self, painter, option, index):
        # Get column role
        role = self.get_column_role(index.column())
        # Set background color
        if role == 'input':
            painter.fillRect(option.rect, QColor(255, 255, 224, 127))  # Light yellow with transparency
        elif role == 'output':
            painter.fillRect(option.rect, QColor(173, 216, 230, 127))  # Light blue with transparency
        # Call super to paint text
        super().paint(painter, option, index)