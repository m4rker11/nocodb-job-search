# transformations/followup_emails.py
import re
from .llm_transformation import MultiLLMTransformation

class FollowUpEmailTransformation(MultiLLMTransformation):
    name = "Professional Follow-Up Emails"
    description = "Generates two polished follow-up emails with achievement highlights"
    predefined_output = True

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

    def transform(self, df, output_col_name, **kwargs):
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
- Applied on: {{Application_Date}}
- Initial outreach: {{First_Email}}
- New achievements: {{Recent_Achievements}}

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
        # Split and validate emails
        email_pairs = df[temp_col].apply(self._split_and_validate_emails)
        
        df["FollowUp_Email_1"] = email_pairs.apply(lambda x: x[0])
        df["FollowUp_Email_2"] = email_pairs.apply(lambda x: x[1])
        df.drop(columns=[temp_col], inplace=True)

    def _split_and_validate_emails(self, text):
        emails = text.split("===EMAIL2===")
        
        # Validate both emails
        cleaned = []
        for email in emails[:2]:  # Only take first two
            validated = self._validate_email(email.strip())
            cleaned.append(validated)
        
        # Handle missing emails
        if len(cleaned) < 2:
            cleaned.append(cleaned[0] if len(cleaned) > 0 else "Email draft needed")
            
        return cleaned[0], cleaned[1]

    def _validate_email(self, text):
        # Check for required components
        checks = [
            (r"^Subject\s*:", "Missing subject line"),
            (r"Dear\s+[A-Za-z]", "Missing personalized greeting"),
            (r"{{Job_Title}}", "Job title reference"),
            (r"(looking forward|eager to)", "Positive language"),
            (r"Best regards?,\n", "Proper sign-off")
        ]
        
        for regex, msg in checks:
            if not re.search(regex, text, re.IGNORECASE):
                text += f"\n\n[NOTE: {msg} - please review]"
                
        # Clean up common errors
        text = re.sub(r"\s+\n", "\n", text)  # Compact whitespace
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # Join broken lines
        
        return text.strip()