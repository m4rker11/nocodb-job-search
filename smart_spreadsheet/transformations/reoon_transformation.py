import logging
import os
import time
import requests
import pandas as pd

from transformations.base import BaseTransformation

logger = logging.getLogger(__name__)

class ReoonVerifierClient:
    def __init__(self):
        self.api_key = os.getenv("REOON_API_KEY", "")
        self.base_url = "https://emailverifier.reoon.com/api/v1/verify"
        if not self.api_key:
            logger.warning("[Reoon] REOON_API_KEY is not set; calls will fail.")

    def verify_email(self, email, timeout=60):
        params = {"key": self.api_key, "email": email, "mode": "power"}
        try:
            response = requests.get(self.base_url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            logger.info(f"[Reoon] Email verification response: {data.get('status')}")
            # "safe" means not disposable & deliverable, etc. 
            return data.get("status") == "safe"
        except requests.exceptions.RequestException as e:
            logger.error(f"[Reoon] API request failed: {e}")
            return None

class ReoonEmailVerificationTransformation(BaseTransformation):
    name = "Reoon Email Verification Transformation"
    description = "Verifies emails using the Reoon API."

    def required_inputs(self):
        # We only need one column: the email
        return ["Email Column"]

    def transform(self, df, output_col_name, *args):
        email_col = args[0]
        reoon_client = ReoonVerifierClient()

        def verify_email(row):
            email = row[email_col]
            is_safe= self._verify_email_with_backoff(reoon_client, email)
            return is_safe

        df[output_col_name] = df.apply(verify_email, axis=1)
        return df

    def _verify_email_with_backoff(self, reoon_client, email):
        max_retries = 5
        delay = 1  # Initial backoff

        for attempt in range(max_retries):
            try:
                return reoon_client.verify_email(email)
            except Exception as e:
                logger.warning(f"[Reoon] Retry {attempt+1}/{max_retries} for '{email}' - {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"[Reoon] Failed to verify '{email}' after {max_retries} attempts: {e}")
                    return None, None
