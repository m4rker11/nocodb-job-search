from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QFileDialog
)
from services.settings_service import (
    get_linkedin_url, set_linkedin_url,
    get_resume_folder, set_resume_folder,
    get_email_account, set_email_account,
    get_email_password, set_email_password
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")

        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 1) Personal Info Tab
        self.personal_tab = QWidget()
        self._setup_personal_tab()
        self.tab_widget.addTab(self.personal_tab, "Personal Info")

        # 2) Email Tab
        self.email_tab = QWidget()
        self._setup_email_tab()
        self.tab_widget.addTab(self.email_tab, "Email")

        # OK/Cancel
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        main_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        main_layout.addWidget(self.cancel_button)

        self.setLayout(main_layout)

    def _setup_personal_tab(self):
        layout = QFormLayout()

        # LinkedIn URL
        self.linkedin_edit = QLineEdit()
        self.linkedin_edit.setText(get_linkedin_url())
        layout.addRow("LinkedIn URL:", self.linkedin_edit)

        # Resume Folder
        row_widget = QWidget()
        from PyQt6.QtWidgets import QHBoxLayout
        row_layout = QHBoxLayout()

        self.resume_edit = QLineEdit()
        self.resume_edit.setText(get_resume_folder())
        row_layout.addWidget(self.resume_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_resume_folder)
        row_layout.addWidget(browse_btn)

        row_widget.setLayout(row_layout)
        layout.addRow("Resume Folder:", row_widget)

        self.personal_tab.setLayout(layout)

    def _browse_resume_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Resume Folder")
        if folder_path:
            self.resume_edit.setText(folder_path)

    def _setup_email_tab(self):
        layout = QFormLayout()

        self.email_account_edit = QLineEdit()
        self.email_account_edit.setText(get_email_account())
        layout.addRow("Email Account:", self.email_account_edit)

        self.email_password_edit = QLineEdit()
        self.email_password_edit.setText(get_email_password())
        self.email_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Email Password:", self.email_password_edit)

        self.email_tab.setLayout(layout)

    def accept(self):
        """
        When user clicks OK, store the changes in QSettings.
        """
        set_linkedin_url(self.linkedin_edit.text().strip())
        set_resume_folder(self.resume_edit.text().strip())
        set_email_account(self.email_account_edit.text().strip())
        set_email_password(self.email_password_edit.text())

        super().accept()
