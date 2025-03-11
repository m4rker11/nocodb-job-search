# ui/compose_email_dialog.py
import json
import webbrowser
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from services.email_service import send_email

class ComposeEmailDialog(QDialog):
    def __init__(self, to_email="", subject="", body="", email_json="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compose Email")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # Initialize with either direct values or from JSON
        if email_json:
            try:
                email_data = json.loads(email_json)
                self.to_email = to_email
                self.subject = email_data.get("subject", "")
                self.body = email_data.get("body", "")
            except json.JSONDecodeError:
                self.to_email = to_email
                self.subject = subject
                self.body = body
        else:
            self.to_email = to_email
            self.subject = subject
            self.body = body

        main_layout = QVBoxLayout()

        # Recipient
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_line = QLineEdit(self.to_email)
        self.to_line.setPlaceholderText("Enter recipient email address")
        to_layout.addWidget(self.to_line)
        main_layout.addLayout(to_layout)

        # Subject
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Subject:"))
        self.subject_line = QLineEdit(self.subject)
        self.subject_line.setPlaceholderText("Enter email subject")
        subject_layout.addWidget(self.subject_line)
        main_layout.addLayout(subject_layout)

        # Body
        self.body_text = QTextEdit()
        self.body_text.setPlainText(self.body)
        self.body_text.setPlaceholderText("Compose your email here...")
        main_layout.addWidget(self.body_text)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

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

        # Validate inputs
        if not to_addr:
            QMessageBox.warning(self, "Missing To", "Recipient email is required.")
            return
        if not subject:
            QMessageBox.warning(self, "Missing Subject", "Email subject is required.")
            return
        if not body.strip():
            QMessageBox.warning(self, "Missing Body", "Email body cannot be empty.")
            return

        # Get the mailto link and open it in the default browser
        success, mailto_link = send_email(to_addr, subject, body)
        
        if success:
            try:
                # Open the mailto link in the default browser/email client
                webbrowser.open(mailto_link)
                QMessageBox.information(self, "Success", "Email opened in your default email client!")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open email client:\n{str(e)}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to create email link:\n{mailto_link}")

    def get_email_json(self):
        """Return the current email content as JSON"""
        return json.dumps({
            "subject": self.subject_line.text().strip(),
            "body": self.body_text.toPlainText()
        }, indent=2)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_Return:
            self.on_send()
        else:
            super().keyPressEvent(event)