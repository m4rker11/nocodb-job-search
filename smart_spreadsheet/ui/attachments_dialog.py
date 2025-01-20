from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QListWidget, QFileDialog
)

class AttachmentsDialog(QDialog):
    """
    Placeholder for managing file attachments.
    Each row might have a set of files associated with it.
    """

    def __init__(self, row_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Attachments for Row {row_id}")
        self.row_id = row_id

        layout = QVBoxLayout()

        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        self.add_button = QPushButton("Add File")
        self.add_button.clicked.connect(self.add_file)
        layout.addWidget(self.add_button)

        self.setLayout(layout)

    def add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Attachment", "", "All Files (*.*)"
        )
        if file_path:
            # TODO: copy the file to a managed attachments folder
            # and store a reference in e.g. a DB or the DataFrame
            self.file_list.addItem(file_path)