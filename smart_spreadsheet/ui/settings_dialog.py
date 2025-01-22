from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QFileDialog, QHBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from services.settings_service import (
    get_linkedin_url, set_linkedin_url,
    get_resume_path, set_resume_path,
    get_email_account, set_email_account,
    get_email_password, set_email_password,
    load_env_vars, get_env_var, set_env_var
)

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(600, 400)
        
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Load environment variables
        load_env_vars()

        # 1) Personal Info Tab
        self.personal_tab = QWidget()
        self._setup_personal_tab()
        self.tab_widget.addTab(self.personal_tab, "Personal Info")

        # 2) Email Tab
        self.email_tab = QWidget()
        self._setup_email_tab()
        self.tab_widget.addTab(self.email_tab, "Email")

        # 3) Environment Variables Tab
        self.env_tab = QWidget()
        self._setup_env_tab()
        self.tab_widget.addTab(self.env_tab, "Env Vars")

        # OK/Cancel Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _setup_personal_tab(self):
        layout = QFormLayout()

        # LinkedIn URL
        self.linkedin_edit = QLineEdit()
        self.linkedin_edit.setText(get_linkedin_url())
        layout.addRow("LinkedIn URL:", self.linkedin_edit)

        # Resume Upload
        resume_widget = QWidget()
        resume_layout = QHBoxLayout()
        
        self.resume_edit = QLineEdit()
        self.resume_edit.setText(get_resume_path())
        self.resume_edit.setReadOnly(True)
        resume_layout.addWidget(self.resume_edit)
        
        browse_btn = QPushButton("Upload Resume...")
        browse_btn.clicked.connect(self._upload_resume)
        resume_layout.addWidget(browse_btn)
        
        resume_widget.setLayout(resume_layout)
        layout.addRow("Resume File:", resume_widget)

        self.personal_tab.setLayout(layout)

    def _upload_resume(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Resume", 
            "", 
            "Documents (*.pdf *.docx)"
        )
        if file_path:
            self.resume_edit.setText(file_path)

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
        self.ollama_url_edit.setText(get_env_var("OLLAMA_URL") or "http://localhost:11434")
        layout.addRow("Ollama URL:", self.ollama_url_edit)

        self.ollama_model_edit = QLineEdit()
        self.ollama_model_edit.setText(get_env_var("OLLAMA_MODEL") or "llama2")
        layout.addRow("Ollama Model:", self.ollama_model_edit)

        self.env_tab.setLayout(layout)

    def accept(self):
        # Update resume path first to trigger parsing
        set_resume_path(self.resume_edit.text().strip())
        
        # Update LinkedIn URL to trigger Wiza lookup
        set_linkedin_url(self.linkedin_edit.text().strip())
        
        # Update email settings
        set_email_account(self.email_account_edit.text().strip())
        set_email_password(self.email_password_edit.text())

        # Update environment variables
        set_env_var("OPENAI_API_KEY", self.openai_api_edit.text().strip())
        set_env_var("ANTHROPIC_API_KEY", self.anthropic_api_edit.text().strip())
        set_env_var("WIZA_API_KEY", self.wiza_api_edit.text().strip())
        set_env_var("REOON_API_KEY", self.reoon_api_edit.text().strip())
        set_env_var("OLLAMA_URL", self.ollama_url_edit.text().strip())
        set_env_var("OLLAMA_MODEL", self.ollama_model_edit.text().strip())

        super().accept()