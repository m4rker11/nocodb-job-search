# services/email_service.py

import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import re
from typing import List, Dict, Tuple, Optional
from services.settings_service import (
    get_email_account,
    get_email_password
)
import os
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# Gmail-specific configurations
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465  # Default to TLS port
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_IMAP_PORT = 993


# Google OAuth imports

# Configuration
GMAIL_OAUTH_SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

class EmailService:
    def __init__(self):
        self.token_file = 'email_token.json'
        self.credentials_file = 'email_credentials.json'
        
    def _get_oauth_credentials(self) -> Optional[Credentials]:
        """Get valid OAuth credentials from storage or auth flow."""
        creds = None
        
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, GMAIL_OAUTH_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing token...")
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, GMAIL_OAUTH_SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the new credentials (including any new refresh token)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
        return creds

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str = "TEst",
        provider_type = 'gmail_oauth',
        smtp_server: str = 'smtp.gmail.com',
        smtp_port: int = 587
    ) -> Tuple[bool, str]:
        """
        Send email using either OAuth 2.0 (Gmail) or traditional SMTP
        """
        try:
            if provider_type == 'gmail_oauth':
                return self._send_gmail_oauth(to_email, subject, body)
            else:
                return self._send_smtp(
                    to_email, subject, body,
                    smtp_server, smtp_port
                )
                
        except Exception as e:
            return False, f"Email sending failed: {str(e)}"

    def _send_gmail_oauth(self, to_email: str, subject: str, body: str) -> Tuple[bool, str]:
        """Send email using Gmail API with OAuth 2.0"""
        try:
            creds = self._get_oauth_credentials()
            service = build('gmail', 'v1', credentials=creds)

            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return True, "Email sent successfully via Gmail API"

        except Exception as e:
            return False, f"Gmail API error: {str(e)}"

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
        smtp_server: str,
        smtp_port: int
    ) -> Tuple[bool, str]:
        """Fallback SMTP method for other providers"""
        try:
            # Get credentials from your configuration
            username = get_email_account()       # e.g. "mygmail@gmail.com"
            password = get_email_password() 

            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_port == 587:
                    server.starttls()
                server.login(username, password)
                server.send_message(msg)

            return True, "Email sent successfully via SMTP"

        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed. Check credentials."
        except Exception as e:
            return False, f"SMTP error: {str(e)}"

    def get_recent_emails(
        self,
        days: int = 1,
        provider_type: str = 'gmail_oauth'
    ) -> List[Dict]:
        """Retrieve recent emails using either method"""
        if provider_type == 'gmail_oauth':
            return self._get_gmail_emails(days)
        else:
            return self._get_imap_emails(days)

    def _get_gmail_emails(self, days: int) -> List[Dict]:
        """Get emails using Gmail API"""
        try:
            creds = self._get_oauth_credentials()
            service = build('gmail', 'v1', credentials=creds)

            query = f'after:{(datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")}'
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=20
            ).execute()

            emails = []
            messages = results.get('messages', [])
            for message in messages:
                msg = service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()
                
                emails.append({
                    'from': next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'),
                    'subject': next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject'),
                    'date': msg['internalDate']
                })

            return emails

        except Exception as e:
            print(f"Gmail API error: {str(e)}")
            return []

def load_incoming_emails_last_24h() -> List[Dict]:
    """Fetch emails using OAuth2 IMAP authentication"""
    try:
        # Get OAuth credentials
        email_service = EmailService()
        creds = email_service._get_oauth_credentials()
        
        # Force token refresh if needed
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
        # Get user email from settings
        user_email = get_email_account()
        
        if not user_email or not creds or not creds.valid:
            raise Exception("Invalid email credentials configuration")

        # IMAP OAuth2 authentication
        mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT)
        auth_string = f'user={user_email}\x01auth=Bearer {creds.token}\x01\x01'
        mail.authenticate('XOAUTH2', lambda x: auth_string.encode())
        mail.select('inbox')

        # Calculate date range
        date_since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        _, search_data = mail.search(None, f'(SINCE "{date_since}")')

        emails = []
        
        # Process emails
        for num in search_data[0].split():
            try:
                _, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                email_details = {
                    'from': msg['from'],
                    'subject': msg['subject'],
                    'body': ''
                }

                # Extract body content
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        email_details['body'] += part.get_payload(decode=True).decode(errors='replace')
                        break  # Prioritize first text/plain part

                emails.append(email_details)
            except Exception as e:
                print(f"Error processing email: {str(e)}")
                continue

        mail.close()
        mail.logout()
        return emails

    except imaplib.IMAP4.error as e:
        print(f"IMAP protocol error: {str(e)}")
        return []
    except Exception as e:
        print(f"Email fetch error: {str(e)}")
        return []
    
def check_emails_for_sender_or_company(
    emails: List[Dict],
    target_sender: str = None,
    company_names: List[str] = None
) -> List[Dict]:
    """
    Check emails for matches from a specific sender or containing company names.
    Args:
        emails (List[Dict]): List of emails to check.
        target_sender (str): Email address of the sender to match.
        company_names (List[str]): List of company names to search for.
    Returns:
        List[Dict]: List of matching emails.
    """
    if not target_sender and not company_names:
        return []

    target_sender = target_sender.lower() if target_sender else None
    company_patterns = [re.compile(re.escape(name.lower()), re.IGNORECASE)
                        for name in company_names] if company_names else []

    matches = []

    for email in emails:
        # Check sender match
        if target_sender and target_sender in email['from'].lower():
            matches.append(email)
            continue

        # Check company name match in subject or body
        if company_patterns:
            text_content = f"{email['subject']} {email['body']}".lower()
            for pattern in company_patterns:
                if pattern.search(text_content):
                    matches.append(email)
                    break  # Avoid duplicate matches

    return matches

def extract_email_address(s: str) -> str:
    """Extract email address from a string containing potential formatting"""
    if not s:
        return ""
    match = re.search(r'[\w\.-]+@[\w\.-]+', s)
    return match.group(0).lower() if match else s.strip().lower()