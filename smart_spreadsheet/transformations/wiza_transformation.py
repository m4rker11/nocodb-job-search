import logging
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv

from transformations.base import BaseTransformation

load_dotenv()
logger = logging.getLogger(__name__)

class WizaAPI:
    def __init__(self):
        self.api_key = os.getenv("WIZA_API_KEY", "")
        if not self.api_key:
            raise ValueError("WIZA_API_KEY is not set.")
        self.base_url = "https://wiza.co/api/"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_individual_reveal(self, linkedin, enrichment_level="partial"):
        url = f"{self.base_url}individual_reveals"
        payload = {
            "individual_reveal": {"profile_url": linkedin},
            "enrichment_level": enrichment_level,
            "callback_url": None,
        }
        resp = requests.post(url, headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()["data"]["id"]

    def get_individual_reveal(self, reveal_id):
        url = f"{self.base_url}individual_reveals/{reveal_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

class WizaIndividualRevealTransformation(BaseTransformation):
    name = "Wiza Individual Reveal Transformation"
    description = "Performs an individual reveal using the Wiza API."

    def required_inputs(self):
        """
        We need three columns: Full Name, Company, Domain.
        """
        return ["Linkedin"]

    def transform(self, df, output_col_name, *args):
        linkedin_col = args[0]
        wiza_api = WizaAPI()

        def perform_reveal(row):
            linkedin = row[linkedin_col]

            # Actually call the reveal
            reveal_id = self._create_reveal_with_backoff(wiza_api, linkedin)
            reveal_data = self._get_reveal_with_backoff(wiza_api, reveal_id)
            return reveal_data

        df[output_col_name] = df.apply(perform_reveal, axis=1)
        return df

    def _create_reveal_with_backoff(self, wiza_api,linkedin):
        max_retries = 5
        delay = 1

        for attempt in range(max_retries):
            try:
                return wiza_api.create_individual_reveal(linkedin)
            except Exception as e:
                logger.warning(
                    f"[Wiza] Retry {attempt+1}/{max_retries} for create_individual_reveal: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise

    def _get_reveal_with_backoff(self, wiza_api, reveal_id):
        max_retries = 5
        delay = 1
        max_polling_attempts = 10
        polling_delay = 5

        for attempt in range(max_retries):
            try:
                for polling_attempt in range(max_polling_attempts):
                    reveal_data = wiza_api.get_individual_reveal(reveal_id)
                    if reveal_data['data']['is_complete']:
                        return reveal_data
                    logger.info(
                        f"[Wiza] Polling attempt {polling_attempt+1}/{max_polling_attempts} for reveal completion."
                    )
                    time.sleep(polling_delay)
                raise TimeoutError("Reveal did not complete within the expected time.")
            except Exception as e:
                logger.warning(
                    f"[Wiza] Retry {attempt+1}/{max_retries} for get_individual_reveal: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise
