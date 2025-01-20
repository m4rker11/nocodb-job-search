from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QFileDialog, QHBoxLayout
)
from services.settings_service import (
    get_linkedin_url, set_linkedin_url,
    get_resume_folder, set_resume_folder,
    get_email_account, set_email_account,
    get_email_password, set_email_password,
    load_env_vars, get_env_var, set_env_var
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")

        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Call load_env_vars so we have the latest .env loaded
        load_env_vars()

        # 1) Personal Info Tab
        self.personal_tab = QWidget()
        self._setup_personal_tab()
        self.tab_widget.addTab(self.personal_tab, "Personal Info")

        # 2) Email Tab
        self.email_tab = QWidget()
        self._setup_email_tab()
        self.tab_widget.addTab(self.email_tab, "Email")

        # 3) Environment Variables Tab (new)
        self.env_tab = QWidget()
        self._setup_env_tab()
        self.tab_widget.addTab(self.env_tab, "Env Vars")

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

    def _setup_env_tab(self):
        """
        Create UI fields for environment variables we care about:
          - OPENAI_API_KEY
          - ANTHROPIC_API_KEY
          - WIZA_API_KEY
          - OLLAMA_URL
          - OLLAMA_MODEL
          - REOON_API_KEY
        """
        layout = QFormLayout()

        self.openai_api_edit = QLineEdit()
        self.openai_api_edit.setText(get_env_var("OPENAI_API_KEY"))
        layout.addRow("OpenAI API Key:", self.openai_api_edit)

        self.anthropic_api_edit = QLineEdit()
        self.anthropic_api_edit.setText(get_env_var("ANTHROPIC_API_KEY"))
        layout.addRow("Anthropic API Key:", self.anthropic_api_edit)

        self.wiza_api_edit = QLineEdit()
        self.wiza_api_edit.setText(get_env_var("WIZA_API_KEY"))
        layout.addRow("Wiza API Key:", self.wiza_api_edit)


        self.reoon_api_edit = QLineEdit()
        self.reoon_api_edit.setText(get_env_var("REOON_API_KEY"))
        layout.addRow("Reoon API Key:", self.reoon_api_edit)

        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setText(get_env_var("OLLAMA_URL") or "http://localhost:11411")
        layout.addRow("Ollama URL:", self.ollama_url_edit)

        self.ollama_model_edit = QLineEdit()
        self.ollama_model_edit.setText(get_env_var("OLLAMA_MODEL") or "llama2-7b")
        layout.addRow("Ollama Model:", self.ollama_model_edit)

        self.env_tab.setLayout(layout)

    def accept(self):
        """
        When user clicks OK, store the changes:
          - QSettings for personal & email.
          - .env for environment variables.
        """
        # 1) Update QSettings-based info
        set_linkedin_url(self.linkedin_edit.text().strip())
        set_resume_folder(self.resume_edit.text().strip())
        set_email_account(self.email_account_edit.text().strip())
        set_email_password(self.email_password_edit.text())

        # 2) Update .env-based info
        set_env_var("OPENAI_API_KEY", self.openai_api_edit.text().strip())
        set_env_var("ANTHROPIC_API_KEY", self.anthropic_api_edit.text().strip())
        set_env_var("WIZA_API_KEY", self.wiza_api_edit.text().strip())
        set_env_var("REOON_API_KEY", self.reoon_api_edit.text().strip())
        set_env_var("OLLAMA_URL", self.ollama_url_edit.text().strip())
        set_env_var("OLLAMA_MODEL", self.ollama_model_edit.text().strip())

        super().accept()
