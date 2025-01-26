# transformations/linkedin_message.py
from .llm_transformation import MultiLLMTransformation

class LinkedInMessageTransformation(MultiLLMTransformation):
    name = "LinkedIn Intro Message"
    description = "Generates sub-300char LinkedIn intro with required elements."
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

    def transform(self, df, output_col_name, *args,**kwargs):
        system_prompt = """You are a career coach crafting LinkedIn connection requests. Messages MUST:
            - Be under 300 characters
            - Start with proper greeting (e.g., "Hi [First Name]")
            - Mention specific job applied for (title/ID)
            - Highlight 1-2 key skills from resume matching job requirements
            - End with clear call to connect
            - NO markdown/placeholders"""

        user_prompt = """Create LinkedIn message for {{Hiring_Manager_Name}} at {{CompanyName}}:
            Job Title: {{Job_Title}} (ID: {{Job_ID}})
            Job Requirements: {{Job_Description}}
            My Resume Highlights: {{user_resume}}
            Their Profile: {{Hiring_Manager_LinkedIn}}

            Include:
            1. Personalized greeting
            2. Mention of position applied for
            3. Top relevant skill from my resume
            4. Connection request"""

        provider = kwargs.get("provider", "OpenAI").strip().lower()
        model_name = kwargs.get("model", "gpt-4").strip()
        api_key = kwargs.get("api_key", "")
        
        self._init_clients(api_key)
        placeholder_wrapper = self.get_placeholder_wrapper()

        for idx, row in df.iterrows():
            try:
                final_system = placeholder_wrapper(system_prompt, row)
                final_user = placeholder_wrapper(user_prompt, row)
                
                response = self._generate_with_retries(
                    provider, model_name, final_system, final_user
                )
                df.at[idx, output_col_name] = response
            except Exception as e:
                df.at[idx, output_col_name] = f"ERROR: {e}"

        return df

    def _generate_with_retries(self, provider, model, system_prompt, user_prompt, max_attempts=3):
        response = self._call_llm(provider, model, system_prompt, user_prompt)
        original_response = response
        
        for attempt in range(max_attempts):
            if len(response) <= 300:
                return response
            
            # Build shortening prompt
            error_msg = []
            if len(response) > 300:
                error_msg.append(f"Current length: {len(response)} characters")
                
            shorten_prompt = (
                f"Revise this message to be under 300 characters while keeping all required elements:\n"
                f"Original message: {response}\n"
                f"Issues to fix: {', '.join(error_msg)}\n"
                "Prioritize keeping: Greeting, job mention, key skill match, and CTA"
            )
            
            response = self._call_llm(provider, model, system_prompt, shorten_prompt)
            
        # Final fallback if still too long
        if len(response) > 300:
            return self._truncate_fallback(original_response)
        return response

    def _truncate_fallback(self, text):
        # Preserve ending punctuation and CTA
        truncated = text[:297].strip()
        if not truncated.endswith((".", "!", "?")):
            truncated += "..."
        return truncated + " [Please edit - max length reached]"