# ui/compose_email_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from services.email_service import EmailService

class ComposeEmailDialog(QDialog):
    def __init__(self, to_email="", subject="", body="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compose Email")

        self.to_email = to_email
        self.subject = subject
        self.body = body

        main_layout = QVBoxLayout()

        # Recipient
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_line = QLineEdit(self.to_email)
        to_layout.addWidget(self.to_line)
        main_layout.addLayout(to_layout)

        # Subject
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Subject:"))
        self.subject_line = QLineEdit(self.subject)
        subject_layout.addWidget(self.subject_line)
        main_layout.addLayout(subject_layout)

        # Body
        self.body_text = QTextEdit()
        self.body_text.setPlainText(self.body)
        main_layout.addWidget(self.body_text)

        # Buttons
        btn_layout = QHBoxLayout()
        self.send_button = QPushButton("Send Email")
        self.send_button.clicked.connect(self.on_send)
        btn_layout.addWidget(self.send_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_button)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def on_send(self):
        to_addr = self.to_line.text().strip()
        subject = self.subject_line.text().strip()
        body = self.body_text.toPlainText()

        if not to_addr:
            QMessageBox.warning(self, "Missing To", "Recipient email is required.")
            return
        service = EmailService()
        success, msg = service.send_email(to_addr, subject, body)
        if success:
            QMessageBox.information(self, "Success", "Email sent successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Sending failed:\n{msg}")
