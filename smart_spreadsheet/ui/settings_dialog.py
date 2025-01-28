from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QPushButton, QTextEdit, QHBoxLayout, QLabel, QGroupBox,
    QScrollArea
)
from PyQt6.QtCore import Qt
from services.settings_service import (
    get_linkedin_url, set_linkedin_url,
    get_resume_text, set_resume_text,
    get_email_account, set_email_account,
    get_email_password, set_email_password,
    load_env_vars, get_env_var, set_env_var
)
# Import your transformation discovery method
from transformations.utils import find_transformations_in_package


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.setMinimumSize(800, 600)

        self.transformations = find_transformations_in_package("transformations")
        self.transform_widgets = {}  # Will map transform_name -> (transform_obj, widget)

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

        # 4) Transformations Tab
        self.transformations_tab = QWidget()
        self._setup_transformations_tab()
        self.tab_widget.addTab(self.transformations_tab, "Transformations")

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

    # --------------------- Existing Tab Setup Methods --------------------
    def _setup_personal_tab(self):
        layout = QVBoxLayout()

        # LinkedIn URL
        linkedin_layout = QHBoxLayout()
        linkedin_layout.addWidget(QLabel("LinkedIn URL:"))
        self.linkedin_edit = QLineEdit()
        self.linkedin_edit.setText(get_linkedin_url())
        linkedin_layout.addWidget(self.linkedin_edit)
        layout.addLayout(linkedin_layout)

        # Resume
        layout.addWidget(QLabel("Resume Text:"))
        self.resume_edit = QTextEdit()
        self.resume_edit.setPlainText(get_resume_text())
        self.resume_edit.setPlaceholderText("Paste your resume text here...")
        layout.addWidget(self.resume_edit)

        self.personal_tab.setLayout(layout)

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

    # --------------------- New Transformations Tab --------------------
    def _setup_transformations_tab(self):
        scroll_area = QScrollArea(self.transformations_tab)
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        v_layout = QVBoxLayout(container)

        # Dynamically add a groupbox for each transform with custom settings
        for tname, transform_cls in self.transformations.items():
            if transform_cls.has_custom_settings():
                group_box = self._create_transform_group(tname, transform_cls)
                v_layout.addWidget(group_box)

        v_layout.addStretch(1)  # push content up
        container.setLayout(v_layout)
        scroll_area.setWidget(container)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.transformations_tab.setLayout(main_layout)

    def _create_transform_group(self, tname, transform_cls):
        """
        Create a group box for a single transformation’s settings.
        """
        group_box = QGroupBox(tname)
        layout = QVBoxLayout(group_box)

        # transformation instance
        transform_obj = transform_cls

        # If create_settings_widget returns a widget, add it
        custom_widget = transform_obj.create_settings_widget(self)
        if custom_widget:
            layout.addWidget(custom_widget)

        self.transform_widgets[tname] = (transform_obj, custom_widget)
        return group_box

    # --------------------- Overriding accept() --------------------
    def accept(self):
        """
        Collect data from each transformation widget and save it.
        Then proceed with saving the normal settings.
        """
        # 1) Save personal & email & env settings
        set_linkedin_url(self.linkedin_edit.text().strip())
        set_resume_text(self.resume_edit.toPlainText().strip())
        set_email_account(self.email_account_edit.text().strip())
        set_email_password(self.email_password_edit.text())

        set_env_var("OPENAI_API_KEY", self.openai_api_edit.text().strip())
        set_env_var("ANTHROPIC_API_KEY", self.anthropic_api_edit.text().strip())
        set_env_var("WIZA_API_KEY", self.wiza_api_edit.text().strip())
        set_env_var("REOON_API_KEY", self.reoon_api_edit.text().strip())
        set_env_var("OLLAMA_URL", self.ollama_url_edit.text().strip())
        set_env_var("OLLAMA_MODEL", self.ollama_model_edit.text().strip())

        # 2) Save transformations that have custom UIs
        for tname, (transform_obj, custom_widget) in self.transform_widgets.items():
            if transform_obj.has_custom_settings() and custom_widget:
                # Gather data from the widget’s fields
                widget_data = {}

                # For the example LinkedIn transformation we know the widget
                # has self.template_edit and self.examples_edit. One approach:
                if hasattr(transform_obj, "template_edit") and hasattr(transform_obj, "examples_edit"):
                    widget_data["template"] = transform_obj.template_edit.toPlainText()
                    widget_data["examples"] = transform_obj.examples_edit.toPlainText()

                transform_obj.save_custom_settings(widget_data)

        super().accept()
