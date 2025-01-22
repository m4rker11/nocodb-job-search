from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QDialog
from PyQt6.QtCore import QTimer

class PromptEditorDialog(QDialog):
    def __init__(self, initial_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Editor")
        self.setMinimumSize(600, 400)
        
        self.layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.layout.addWidget(self.text_edit)
        
        # Auto-save timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.auto_save)
        self.timer.start(5000)  # 5 seconds
        
        self.setLayout(self.layout)

    def auto_save(self):
        if self.parent():
            self.parent().current_prompt_draft = self.text_edit.toPlainText()
            
    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)