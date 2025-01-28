# transformations/linkedin_message.py

from .llm_transformation import MultiLLMTransformation
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit

class LinkedInMessageTransformation(MultiLLMTransformation):
    name = "LinkedIn Intro Message"
    description = "Generates sub-300char LinkedIn intro with required elements."
    predefined_output = True

    _template_file = "linkedin_template.txt"
    _examples_file = "linkedin_few_shot.txt"

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
                "default": "gpt-4"
            },
            {
                "name": "api_key",
                "type": "text",
                "description": "API key (leave blank for environment variable)"
            }
        ]

    def transform(self, df, output_col_name, *args, **kwargs):
        """
        Incorporate user template/few-shot into system/user prompts,
        then call the LLM with re-try logic to ensure sub-300 char messages.
        """
        # 1) Load user's custom template & examples
        settings = self.load_custom_settings()
        user_template = settings.get("template", "")
        user_few_shot = settings.get("examples", "")

        # 2) Original, built-in base prompts
        base_system_prompt = """You are a personable career coach crafting LinkedIn connection requests for a client. Messages MUST:
            - Be under 300 characters
            - Start with proper greeting (e.g., "Hi [First Name]")
            - Mention specific job applied for (title/ID)
            - Highlight 1-2 key skills from resume matching job requirements
            - End with clear call to connect
            - Be on a 6th grade reading level and sound like an feeling person
            - NO markdown/placeholders
        """
        base_user_prompt = """Create LinkedIn message for {{Hiring_Manager_Name}} at {{CompanyName}}:
            Job Title: {{Job_Title}} (ID: {{Job_ID}})
            Job Requirements: {{Job_Description}}
            My Resume Highlights: {{user_resume}}
            Their Profile: {{LinkedIn_Summary}}
            My name you can find in the resume.

            Include:
            1. Personalized greeting
            2. Mention of position applied for
            3. Top relevant skill from my resume
            4. Connection request
            5. Signature 
        """

        # 3) Merge user-provided text with base prompts:
        #    - Example: prepend the user template to the system prompt
        #               prepend the few-shot examples to the user prompt
        if user_template:
            base_system_prompt = base_system_prompt.strip() + "\n\n" + f"Here is the template you should follow: {user_template.strip()}\n\n"
        if user_few_shot:
            base_system_prompt = base_system_prompt.strip() + "\n\n" + f"Here are some examples of messages that worked in the past: {user_few_shot.strip()}"

        # 4) Set up LLM call parameters
        provider = kwargs.get("provider", "OpenAI").strip().lower()
        model_name = kwargs.get("model", "gpt-4").strip()

        self._init_clients()
        placeholder_wrapper = self.get_placeholder_wrapper()

        # 5) For each row, do placeholder substitution, then generate the message
        for idx, row in df.iterrows():
            try:
                final_system = placeholder_wrapper(base_system_prompt, row)
                final_user = placeholder_wrapper(base_user_prompt, row)

                response = self._generate_with_retries(
                    provider, model_name, final_system, final_user
                )
                df.at[idx, output_col_name] = response
            except Exception as e:
                df.at[idx, output_col_name] = f"ERROR: {e}"

        return df

    def _generate_with_retries(self, provider, model, system_prompt, user_prompt, max_attempts=3):
        """
        Calls LLM, checks length, and tries to shorten if >300 characters.
        """
        response = self._call_llm(provider, model, system_prompt, user_prompt)
        original_response = response

        for attempt in range(max_attempts):
            if len(response) <= 300:
                return response

            # Build a 'shortening prompt'
            error_msg = [f"Current length: {len(response)} characters"]
            shorten_prompt = (
                "Revise this message to be under 300 characters while keeping "
                "all required elements:\n"
                f"Original message: {response}\n"
                f"Issues to fix: {', '.join(error_msg)}\n"
                "Prioritize keeping: Greeting, job mention, key skill match, and CTA"
            )

            # Re-run with the shorten prompt as user prompt
            response = self._call_llm(provider, model, system_prompt, shorten_prompt)

        # Final fallback if still too long
        if len(response) > 300:
            return self._truncate_fallback(original_response)
        return response

    def _truncate_fallback(self, text):
        truncated = text[:297].rstrip()
        if not truncated.endswith((".", "!", "?")):
            truncated += "..."
        return truncated + " [Please edit - max length reached]"

    #
    # -------- Settings UI Methods --------
    #
    def has_custom_settings(self) -> bool:
        return True

    def create_settings_widget(self, parent=None) -> QWidget:
        """
        Returns a widget with two QPlainTextEdits: one for 'template',
        one for 'few-shot examples.'
        """
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("LinkedIn Message Template:"))
        self.template_edit = QPlainTextEdit()
        self.template_edit.setPlainText(self.load_custom_settings().get("template", ""))
        layout.addWidget(self.template_edit)

        layout.addWidget(QLabel("Few-Shot Examples (optional):"))
        self.examples_edit = QPlainTextEdit()
        self.examples_edit.setPlainText(self.load_custom_settings().get("examples", ""))
        layout.addWidget(self.examples_edit)

        return widget

    def load_custom_settings(self):
        """
        Read from text files. Return a dict
        with 'template' and 'examples' for pre-filling the UI.
        """
        data = {"template": "", "examples": ""}

        if os.path.exists(self._template_file):
            with open(self._template_file, "r", encoding="utf-8") as f:
                data["template"] = f.read()

        if os.path.exists(self._examples_file):
            with open(self._examples_file, "r", encoding="utf-8") as f:
                data["examples"] = f.read()

        return data

    def save_custom_settings(self, widget_data: dict):
        """
        Save updated text into local files.
        """
        template_text = widget_data.get("template", "")
        examples_text = widget_data.get("examples", "")

        with open(self._template_file, "w", encoding="utf-8") as f:
            f.write(template_text)

        with open(self._examples_file, "w", encoding="utf-8") as f:
            f.write(examples_text)
