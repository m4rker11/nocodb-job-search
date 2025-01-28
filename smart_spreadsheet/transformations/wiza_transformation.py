import logging
import os
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from transformations.base import BaseTransformation
from transformations.reoon_transformation import ReoonVerifierClient
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
            "email_options": {"accept_work": True, "accept_personal": True},
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
    
    def get_profile_data(self, linkedin_url):
        """Direct access method for single profile lookup"""
        reveal_id = self.create_individual_reveal(linkedin_url)
        max_retries = 5
        delay = 1
        max_polling_attempts = 10
        polling_delay = 5

        for attempt in range(max_retries):
            try:
                for polling_attempt in range(max_polling_attempts):
                    reveal_data = self.get_individual_reveal(reveal_id)
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

class WizaIndividualRevealTransformation(BaseTransformation):
    name = "Wiza Individual Reveal Transformation"
    description = "Extracts verified emails and professional information from LinkedIn profiles."
    predefined_output = True  # Override the flag
    output_columns = [  # Define fixed columns
        'Email', 
        'LinkedIn_Summary'
    ]

    def required_inputs(self):
        return ["Linkedin"]

    def transform(self, df, output_col_name, *args):
        # Ignore output_col_name since we're using predefined columns
        linkedin_col = args[0]
        wiza_api = WizaAPI()
        reoon_client = ReoonVerifierClient()

        # Initialize all output columns if missing
        for col in self.output_columns:
            if col not in df.columns:
                df[col] = None

        def perform_reveal(row):
            linkedin_url = row[linkedin_col]
            if pd.isna(linkedin_url) or not linkedin_url.strip():
                return row

            try:
                reveal_data = wiza_api.get_profile_data(linkedin_url)
                data = reveal_data.get('data', {})
                
                # Extract and verify emails
                personal_email, work_email = self._process_emails(data, reoon_client)
                
                # Build professional summary


                # Update row with extracted data
                row['Email'] = work_email if work_email else personal_email
                row['LinkedIn_Summary'] = data
                row["Hiring_Manager_Name"] = data.get("name", row["Hiring_Manager_Name"])

            except Exception as e:
                logger.error(f"[Wiza] Error processing row: {e}")

            return row

        return df.apply(perform_reveal, axis=1)

    def _process_emails(self, data, reoon_client):
        personal_email = None
        work_email = None
        for email_info in data.get('emails', []):
            email = email_info.get('email')
            if not email:
                continue
                
            if reoon_client.verify_email(email):
                email_type = email_info.get('type', '').lower()
                if email_type == 'personal':
                    personal_email = email
                elif email_type == 'work':
                    work_email = email
        return personal_email, work_email



    def _build_summary(self, data):
        summary_parts = []
        for field in ['summary', 'company description', 'name', 'title', 'location', 'subtitle', 'certifications', 'education', 'work_history']:
            summary_parts.append(f"\n\n{data.get(field)}")
        return ' - '.join(summary_parts) if summary_parts else None