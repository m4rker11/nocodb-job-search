# transformations/llm_transformation.py
import os
import time
import requests
import openai
import anthropic
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from transformations.base import BaseTransformation, SafeTemplate

class MultiLLMTransformation(BaseTransformation):
    name = "Multi-Provider LLM Transformation"
    description = "Calls OpenAI, Anthropic, or Ollama with templated prompts."

    def required_inputs(self):
        return []  # No direct column inputs

    def required_static_params(self):
        return [
            {
                "name": "system_prompt",
                "type": "prompt",
                "description": "System role prompt template with {{placeholders}}"
            },
            {
                "name": "user_prompt", 
                "type": "prompt",
                "description": "User prompt template with {{placeholders}}"
            },
            {
                "name": "provider",
                "type": "combobox",
                "options": ["OpenAI", "Anthropic", "Ollama", "DeepSeek"],
                "default": "Ollama"
            },
            {
                "name": "model",
                "type": "combobox",
                "options": [],
                "editable": True,
                "description": "Model name based on provider",
                "default": "llama3.1:8b"
            },
            {
                "name": "api_key",
                "type": "text",
                "description": "API key (leave blank for environment variable)"
            }
        ]

    def transform(
        self,
        df,
        output_col_name,
        system_prompt,
        user_prompt,
        extra_placeholders=None,
        json_mode=False,
        *args,
        **kwargs
    ):
        provider = kwargs.get("provider", "OpenAI").strip().lower()
        model_name = kwargs.get("model", "gpt-4o-mini").strip()
        if extra_placeholders is None:
            extra_placeholders = {}
        # Initialize clients
        
        placeholder_wrapper = self.get_placeholder_wrapper(extra_placeholders)
        # Process prompts for each row
        for idx, row in df.iterrows():
            try:
                final_system = placeholder_wrapper(system_prompt, row)
                final_user = placeholder_wrapper(user_prompt, row)
                response = self._call_llm(provider, model_name, final_system, final_user, json_mode)
                df.at[idx, output_col_name] = response
            except Exception as e:
                df.at[idx, output_col_name] = f"ERROR: {e}"

        return df

    def _init_clients(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        self.anthropic_client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )

    def _call_llm(self, provider, model_name, system_prompt, user_prompt, json_mode=False, max_retries=3):
        delay = 2
        self._init_clients()
        for attempt in range(max_retries):
            try:
                if provider == "openai":
                    return self._call_openai(model_name, system_prompt, user_prompt, json_mode)
                elif provider == "anthropic":
                    return self._call_anthropic(model_name, system_prompt, user_prompt)
                elif provider == "ollama":
                    return self._call_ollama(model_name, system_prompt, user_prompt)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e

    def _call_openai(self, model_name, system_prompt, user_prompt, json_mode=False):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        completion = self.openai_client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"} if json_mode else None
        )
        return completion.choices[0].message.content.strip()

    def _call_anthropic(self, model_name, system_prompt, user_prompt):
        message = self.anthropic_client.messages.create(
            model=model_name,
            system=system_prompt,
            max_tokens=4000,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )
        return message.content[0].text.strip()

    def _call_ollama(self, model_name, system_prompt, user_prompt):
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model_name,
            "prompt": system_prompt + "\n\n" + user_prompt,
            "stream": False,
            "temperature": 0.7
        }
        logger.debug(payload)
        resp = requests.post(url, json=payload, timeout=120)
        if resp.status_code != 200:
            raise ValueError(f"Ollama error: {resp.status_code} - {resp.text}")
        return resp.json().get("response", "").strip()