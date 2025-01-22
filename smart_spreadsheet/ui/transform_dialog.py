from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QComboBox, QLineEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
class TransformDialog(QDialog):
    def __init__(self, transformation, df_columns, parent=None):
        super().__init__(parent)
        self.transformation = transformation
        self.df_columns = df_columns
        self.static_params_widgets = {}
        self.input_col_widgets = []
        self.info_icons = {}
        self.setWindowTitle(f"Configure {transformation.name}")
        self.layout = QVBoxLayout()

        # Input columns
        for input_label in transformation.required_inputs():
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{input_label}:"))
            combo = QComboBox()
            combo.addItems(df_columns)
            self.input_col_widgets.append(combo)
            row.addWidget(combo)
            self.layout.addLayout(row)

        for param in getattr(transformation, 'required_static_params', lambda: [])():
            param_row, widget = self._create_param_row(param)
            self.static_params_widgets[param["name"]] = widget
            self.layout.addLayout(param_row)
        
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
        # Output column
        self.output_edit = QLineEdit()
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Column:"))
        output_layout.addWidget(self.output_edit)
        self.layout.addLayout(output_layout)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)
        self.setStyleSheet("""
            QLabel[infoIcon] {
                color: #2E86C1;
                text-decoration: underline;
            }
            QLabel[infoIcon]:hover {
                color: #1B4F72;
            }
        """)
        # Set the property for info icon
        if "model" in self.info_icons:
            self.info_icons["model"].setProperty("infoIcon", True)
    def get_selections(self):
        return {
            "input_cols": [w.currentText() for w in self.input_col_widgets],
            "output_col": self.output_edit.text().strip(),
            "static_params": {
                name: widget.currentText() if isinstance(widget, QComboBox) else widget.text()
                for name, widget in self.static_params_widgets.items()
            }
        }
    def _create_param_row(self, param):
        row = QHBoxLayout()
        row.addWidget(QLabel(f"{param['name']}:"))
        
        # Create widget
        if param["type"] == "combobox":
            widget = QComboBox()
            widget.addItems(param.get("options", []))
            if param.get("editable", False):
                widget.setEditable(True)
        elif param["type"] == "text":
            widget = QLineEdit()
            widget.setPlaceholderText(param.get("description", ""))
        
        # Add info icon if parameter is 'model'
        if param["name"] == "model":
            info_icon = QLabel("(i)")
            info_icon.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            info_icon.setToolTip(str({
                "OpenAI": ["gpt-4o", "gpt-3.5-turbo"],
                "Anthropic": ["claude-3-haiku", "claude-3-sonnet"],
                "Ollama": ["llama2", "mistral"],
                "DeepSeek": ["deepseek-chat"]
            }))
            info_icon.setCursor(Qt.CursorShape.PointingHandCursor)
            self.info_icons["model"] = info_icon
            row.addWidget(info_icon)
        
        row.addWidget(widget)
        return row, widget
