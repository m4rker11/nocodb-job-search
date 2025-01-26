# transformations/followup_emails.py
import json
import re
from .llm_transformation import MultiLLMTransformation

class FollowUpEmailTransformation(MultiLLMTransformation):
    name = "Professional Follow-Up Emails"
    description = "Generates two polished follow-up emails with achievement highlights"
    predefined_output = True

    def required_inputs(self):
        return ["Hiring_Manager_Name", "CompanyName", "Job_Title", "Job_ID", "LinkedIn_Intro", "Job_Description"]
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
        system_prompt = """You are an executive communications assistant crafting job follow-up emails. Create emails that:
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
            6. Professional sign-off"""

        user_prompt = """Generate two follow-up emails for {{Hiring_Manager_Name}} at {{CompanyName}}:

            Context:
            - Position: {{Job_Title}} (ID: {{Job_ID}})
            - Linkedin Connection Message: {{LinkedIn_Intro}}

            Email 1 (1-week follow-up):
            - Purpose: Enthusiastic check-in
            - Include: Specific role interest, availability for questions

            Email 2 (2-week follow-up):
            - Purpose: Value-add update
            - Include: Relevant new achievement from resume, specific role fit

            Separate emails with ===EMAIL2===
            NO markdown, use proper email formatting"""

        provider = kwargs.get("provider", "OpenAI").strip().lower()
        model_name = kwargs.get("model", "gpt-4").strip()
        api_key = kwargs.get("api_key", "")
        
        self._init_clients(api_key)
        placeholder_wrapper = self.get_placeholder_wrapper()

        temp_col = "__temp_followups"
        df = super().transform(df, temp_col,
                             system_prompt=system_prompt,
                             user_prompt=user_prompt,
                             **kwargs)

        if temp_col in df.columns:
            self._process_emails(df, temp_col)
            
        return df

    def _process_emails(self, df, temp_col):
        """Process generated emails into JSON format"""
        email_pairs = df[temp_col].apply(self._split_and_validate_emails)
        
        df["FollowUp_Email_1"] = email_pairs.apply(lambda x: x[0])
        df["FollowUp_Email_2"] = email_pairs.apply(lambda x: x[1])
        df.drop(columns=[temp_col], inplace=True)

    def _split_and_validate_emails(self, text):
        """Split emails and convert to JSON format"""
        emails = text.split("===EMAIL2===")
        cleaned = []
        
        for email in emails[:2]:  # Only take first two
            email_json = self._convert_to_json(email)
            cleaned.append(email_json)
        
        # Handle missing emails
        if len(cleaned) < 2:
            default_email = json.dumps({
                "subject": "Follow-Up Needed",
                "body": "Email draft pending"
            })
            cleaned.append(default_email)
            
        return cleaned[0], cleaned[1]

    def _convert_to_json(self, email_text):
        """Convert raw email text to JSON format"""
        subject_match = re.search(r'^Subject:\s*(.+?)\n', email_text, re.IGNORECASE|re.MULTILINE)
        subject = subject_match.group(1).strip() if subject_match else "Follow-Up"
        
        # Remove subject line from body
        body = re.sub(r'^Subject:\s*.+?\n', '', email_text, count=1, flags=re.IGNORECASE|re.MULTILINE).strip()
        
        return json.dumps({
            "subject": subject,
            "body": body
        }, indent=2)
