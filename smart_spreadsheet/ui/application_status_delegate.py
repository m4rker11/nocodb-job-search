from PyQt6.QtWidgets import QStyledItemDelegate, QComboBox
from PyQt6.QtCore import Qt

class ApplicationStatusDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.options = ["applied", "linkedin", "emailed", "called", "interviewing", "rejected"]

    def createEditor(self, parent, option, index):
        model = index.model()
        col_name = model.headerData(index.column(), Qt.Orientation.Horizontal)
        if col_name == "Application Status":
            editor = QComboBox(parent)
            editor.addItems(self.options)
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            text = index.model().data(index, Qt.ItemDataRole.EditRole)
            idx = editor.findText(text)
            if idx >= 0:
                editor.setCurrentIndex(idx)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            text = editor.currentText()
            model.setData(index, text, Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)