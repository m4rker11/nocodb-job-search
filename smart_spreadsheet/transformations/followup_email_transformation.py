# transformations/followup_emails.py

import json
import re
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit
from .llm_transformation import MultiLLMTransformation

class FollowUpEmailTransformation(MultiLLMTransformation):
    name = "Professional Follow-Up Emails"
    description = "Generates two polished follow-up emails with achievement highlights"
    predefined_output = True

    # Where we might store user-provided config
    _template_file = "followup_template.txt"
    _few_shot_file = "followup_few_shot.txt"

    def has_custom_settings(self) -> bool:
        return True

    def create_settings_widget(self, parent=None) -> QWidget:
        """
        Returns a small widget with two QPlainTextEdits: one for an
        optional 'template' and one for a 'few-shot' text.
        """
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Follow-Up Email Template:"))
        self.template_edit = QPlainTextEdit()
        self.template_edit.setPlainText(
            self.load_custom_settings().get("template", "")
        )
        layout.addWidget(self.template_edit)

        layout.addWidget(QLabel("Few-Shot Examples (optional):"))
        self.few_shot_edit = QPlainTextEdit()
        self.few_shot_edit.setPlainText(
            self.load_custom_settings().get("few_shot", "")
        )
        layout.addWidget(self.few_shot_edit)

        return widget

    def load_custom_settings(self):
        """
        Reads the template & few-shot text from local files (or you could
        store them in QSettings/JSON). Returns a dict with 'template'/'few_shot'.
        """
        data = {"template": "", "few_shot": ""}
        if os.path.exists(self._template_file):
            with open(self._template_file, "r", encoding="utf-8") as f:
                data["template"] = f.read()

        if os.path.exists(self._few_shot_file):
            with open(self._few_shot_file, "r", encoding="utf-8") as f:
                data["few_shot"] = f.read()

        return data

    def save_custom_settings(self, widget_data: dict):
        """
        Saves the updated text into local files once user hits 'OK' in SettingsDialog.
        """
        template_text = widget_data.get("template", "")
        few_shot_text = widget_data.get("few_shot", "")

        with open(self._template_file, "w", encoding="utf-8") as f:
            f.write(template_text)

        with open(self._few_shot_file, "w", encoding="utf-8") as f:
            f.write(few_shot_text)

    def required_inputs(self):
        return [
            "Hiring_Manager_Name", "CompanyName", "Job_Title", "Job_ID",
            "LinkedIn_Intro", "Job_Description"
        ]

    def required_static_params(self):
        return [
            {
                "name": "provider",
                "type": "combobox",
                "options": ["OpenAI", "Anthropic", "Ollama", "DeepSeek"],
                "default": "OpenAI"
            },
            {
                "name": "model",
                "type": "combobox",
                "options": [],
                "editable": True,
                "description": "Model name based on provider",
                "default": "gpt-4o-mini"
            },
            {
                "name": "api_key",
                "type": "text",
                "description": "API key (leave blank for environment variable)"
            }
        ]

    def transform(self, df, output_col_name, *args, **kwargs):
        # 1) Load the user-provided template & few_shot
        settings = self.load_custom_settings()
        user_template = settings.get("template", "")
        user_few_shot = settings.get("few_shot", "")

        # 2) Incorporate them into your main prompts
        base_system_prompt = """You are an executive communications assistant crafting job follow-up emails. Create emails that:
            - Maintain professional yet personable tone
            - Reference specific company/job details
            - Highlight relevant achievements naturally
            - Show enthusiasm without desperation
            - Use proper business email structure
            - Keep under 150 words per email

            Structure each email:
            1. Clear subject line with job reference
            2. Personalized greeting
            3. Specific reason for following up
            4. New value-add information
            5. Polite call to action
            6. "Patiently Waiting in Interview Limbo" sign-off for the first email and "Your Future Favorite Co-Worker (Fingers Crossed)," for the second
            Return the emails in this exact JSON format:
    {
        "email1": {
            "subject": "Clear subject line with job reference",
            "body": "Full email body with proper greeting and signature"
        },
        "email2": {
            "subject": "Clear subject line with job reference",
            "body": "Full email body with proper greeting and signature"
        }
    }"""


        user_prompt = """Generate two follow-up emails for {{Hiring_Manager_Name}} at {{CompanyName}}:

            Context:
            - Position: {{Job_Title}} (ID: {{Job_ID}})
            - Job Description: {{Job_Description}}
            - My Background and resume (use my name for signature): {{user_resume}} -
            - Linkedin Connection Message: {{LinkedIn_Intro}}

            Email 1 (1-week follow-up):
            - Purpose: Enthusiastic check-in
            - Include: Specific role interest, availability for questions

            Email 2 (2-week follow-up):
            - Purpose: Value-add update
            - Include: Relevant new achievement from resume, specific role fit

            Separate emails with ===EMAIL2===
            NO markdown, use proper email formatting"""

        if user_template:
            base_system_prompt = base_system_prompt.strip() + "\n\n" + f"Here is the template you should follow: {user_template.strip()}\n\n"
        if user_few_shot:
            base_system_prompt = base_system_prompt.strip() + "\n\n" + f"Here are some examples of messages that worked in the past: {user_few_shot.strip()}"

        # Initialize LLM clients
        self._init_clients()
        placeholder_wrapper = self.get_placeholder_wrapper()

        # Process row by row
        for idx, row in df.iterrows():
            try:
                final_system = placeholder_wrapper(base_system_prompt, row)
                final_user = placeholder_wrapper(user_prompt, row)

                # Generate emails using LLM
                response = self._call_llm(
                    kwargs.get("provider", "OpenAI").strip().lower(),
                    kwargs.get("model", "gpt-4o-mini").strip(),
                    final_system,
                    final_user
                )

                # Parse JSON response
                email_data = json.loads(response)
                df.at[idx, "FollowUp_Email_1"] = json.dumps(email_data["email1"])
                df.at[idx, "FollowUp_Email_2"] = json.dumps(email_data["email2"])
                
            except Exception as e:
                df.at[idx, "FollowUp_Email_1"] = f"ERROR: {e}"
                df.at[idx, "FollowUp_Email_2"] = f"ERROR: {e}"

        return df
