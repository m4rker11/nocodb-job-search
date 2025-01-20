import os
import time
import requests
import openai
import anthropic
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from transformations.base import BaseTransformation

class MultiLLMTransformation(BaseTransformation):
    """
    A transformation that can call:
      - OpenAI
      - Anthropic (Claude)
      - Ollama (self-hosted)

    You configure which provider + model to use in the transformation’s metadata
    (rather than storing that in each row).

    required_inputs() expects only the Prompt Column. 
    The provider and model_name will be stored in metadata (or passed as extra kwargs).
    """

    name = "Multi-Provider LLM Transformation"
    description = "Calls OpenAI, Anthropic, or Ollama with a user-selected provider & model."

    def required_inputs(self):
        """
        Only the prompt column is mandatory, because the provider/model will be
        chosen once (via transformation config in metadata).
        """
        return ["Prompt Column"]

    def transform(self, df, output_col_name, *args, **kwargs):
        """
        We expect:
          - args[0] = the name of the prompt column
          - kwargs["provider"] = "openai" or "anthropic" or "ollama"
          - kwargs["model_name"] = model ID/label (e.g. "gpt-4", "claude-2", "llama2-7b" ...)

        For each row, we read the prompt from the prompt column,
        then call the chosen LLM with the same provider & model.
        """
        prompt_col = args[0]

        # Extract from metadata / user config
        provider = kwargs.get("provider", "openai").strip().lower()
        model_name = kwargs.get("model_name", "gpt-4").strip()

        # Set keys
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not openai_api_key:
            print("[WARN] OPENAI_API_KEY not set. OpenAI calls will fail if used.")
        if not anthropic_api_key:
            print("[WARN] ANTHROPIC_API_KEY not set. Anthropic calls will fail if used.")

        # Set up OpenAI
        openai.api_key = openai_api_key
        
        # Set up Anthropic
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)


        # For each row, get the prompt and call the chosen model
        for idx, row in df.iterrows():
            prompt_text = str(row[prompt_col])
            try:
                response = self._call_llm(provider, model_name, prompt_text)
                df.at[idx, output_col_name] = response
            except Exception as e:
                df.at[idx, output_col_name] = f"ERROR: {e}"

        return df

    def _call_llm(self, provider, model_name, prompt_text, max_retries=3):
        delay = 2  # seconds
        for attempt in range(max_retries):
            try:
                if provider == "openai":
                    return self._call_openai(model_name, prompt_text)
                elif provider == "anthropic":
                    return self._call_anthropic(model_name, prompt_text)
                elif provider == "ollama":
                    return self._call_ollama(model_name, prompt_text)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2  # exponential backoff
                else:
                    raise e

    def _call_openai(self, model_name, prompt_text):
        # Create an OpenAI client instance
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Use the client to create a chat completion
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.7,
        )
        
        # Access the message content using dot notation
        return completion.choices[0].message.content.strip()
    def _call_anthropic(self, model_name, prompt_text):
        # Example usage: anthropic Claude
        resp = self.anthropic_client.completions.create(
            model=model_name, 
            max_tokens_to_sample=8000,
            prompt=f"{anthropic.HUMAN_PROMPT} {prompt_text}{anthropic.AI_PROMPT}",
            temperature=0.7,
        )
        return resp.completion.strip()

    def _call_ollama(self, model_name, prompt_text):
        # Example usage for local Ollama
        url = "http://localhost:11411/generate"
        payload = {
            "prompt": prompt_text,
            "model": model_name,
            "temperature": 0.7,
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            raise ValueError(f"Ollama error: {resp.status_code} - {resp.text}")
        data = resp.json()
        return data.get("completion", "").strip()
