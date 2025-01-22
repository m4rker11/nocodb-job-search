from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QLineEdit, QDialogButtonBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QMouseEvent

class PromptEditorDialog(QDialog):
    def __init__(self, initial_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Editor")
        self.setMinimumSize(800, 600)
        
        self.layout = QVBoxLayout()
        
        # Text Edit Area
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.layout.addWidget(self.text_edit)
        
        # Button Box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Auto-save Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_save)
        self.timer.start(5000)  # 5 seconds
        
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def _auto_save(self):
        """Save draft to parent's current_prompt_draft"""
        if self.parent():
            self.parent().current_prompt_draft = self.text_edit.toPlainText()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

class PromptLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Double-click to edit...")
        
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        # Save initial state
        initial_text = self.text()
        
        # Create editor with current text
        editor = PromptEditorDialog(self.text(), self.parent())
        
        # Restore parent's draft if canceled
        if editor.exec() != QDialog.DialogCode.Accepted:
            if self.parent():
                self.parent().current_prompt_draft = initial_text
        else:
            self.setText(self.parent().current_prompt_draft)
        
        # Ensure timer stops
        editor.timer.stop()

class TransformDialog(QDialog):
    def __init__(self, transformation, df_columns, placeholder_wrapper, parent=None):
        super().__init__(parent)
        self.transformation = transformation
        self.df_columns = df_columns
        self.placeholder_wrapper = placeholder_wrapper
        self.static_params_widgets = {}
        self.input_col_widgets = []
        self.info_icons = {}
        self.current_prompt_draft = ""
        
        self.setWindowTitle(f"Configure {transformation.name}")
        self.layout = QVBoxLayout()

        # Input columns (if any)
        for input_label in transformation.required_inputs():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{input_label}:"))
            combo = QComboBox()
            combo.addItems(df_columns)
            self.input_col_widgets.append(combo)
            row.addWidget(combo)
            self.layout.addLayout(row)
        self.model_descriptions = {
            "OpenAI": {
                "gpt-4o": "Most capable vision model",
                "gpt-3.5-turbo": "Fast and cost-effective"
            },
            "Anthropic": {
                "claude-3-haiku": "Fast and affordable",
                "claude-3-sonnet": "Balance of intelligence and speed"
            },
            "Ollama": {
                "llama2": "Meta's LLM (7B-70B parameters)",
                "mistral": "High-quality 7B model"
            },
            "DeepSeek": {
                "deepseek-chat": "Chinese-oriented conversational AI"
            }
        }

        # Static parameters
        for param in getattr(transformation, 'required_static_params', lambda: [])():
            param_row, widget = self._create_param_row(param)
            self.static_params_widgets[param["name"]] = widget
            self.layout.addLayout(param_row)

        # Model descriptions
        
        # Output column
        self.output_edit = QLineEdit()
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Column:"))
        output_layout.addWidget(self.output_edit)
        self.layout.addLayout(output_layout)

        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)
        self._setup_styles()

    def _setup_styles(self):
        self.setStyleSheet("""
            QLabel[infoIcon] {
                color: #2E86C1;
                text-decoration: underline;
            }
            QLabel[infoIcon]:hover {
                color: #1B4F72;
            }
            PromptLineEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 5px;
            }
        """)

    def get_selections(self):
        return {
            "input_cols": [w.currentText() for w in self.input_col_widgets],
            "output_col": self.output_edit.text().strip(),
            "static_params": {
                name: widget.currentText() if isinstance(widget, QComboBox) else widget.text()
                for name, widget in self.static_params_widgets.items()
            },
            "placeholder_wrapper": self.placeholder_wrapper
        }

    def _create_param_row(self, param):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"{param['name']}:"))

        # Create appropriate widget
        if param["type"] == "combobox":
            widget = QComboBox()
            widget.addItems(param.get("options", []))
            if param.get("editable", False):
                widget.setEditable(True)
        elif param["type"] == "prompt":
            widget = PromptLineEdit()
            widget.setPlaceholderText(param.get("description", ""))
        else:  # text
            widget = QLineEdit()
            widget.setPlaceholderText(param.get("description", ""))

        # Add info icon for model parameter
        if param["name"] == "model":
            info_icon = QLabel("(i)")
            info_icon.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            info_icon.setToolTip(self._model_tooltip_text())
            info_icon.setCursor(Qt.CursorShape.PointingHandCursor)
            info_icon.setProperty("infoIcon", True)
            self.info_icons["model"] = info_icon
            row.addWidget(info_icon)

        row.addWidget(widget)
        return row, widget

    def _model_tooltip_text(self):
        text = "Available models:\n"
        for provider, models in self.model_descriptions.items():
            text += f"\n{provider}:\n"
            for model, desc in models.items():
                text += f"  • {model}: {desc}\n"
        return text.strip()