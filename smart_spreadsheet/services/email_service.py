# services/email_service.py

import re
from typing import List, Dict, Tuple, Optional
import urllib.parse

def create_mailto_link(
    to_email: str,
    subject: str,
    body: str = ""
) -> str:
    """
    Creates a mailto: URL that will open the user's default email client
    with the to, subject, and body fields pre-populated.
    
    Args:
        to_email: The recipient's email address
        subject: The email subject line
        body: The email body content
        
    Returns:
        A formatted mailto: URL string
    """
    # URL encode the parameters
    params = {
        'subject': subject,
        'body': body
    }
    
    query_string = urllib.parse.urlencode(params)
    mailto_link = f"mailto:{to_email}?{query_string}"
    
    return mailto_link

def send_email(
    to_email: str,
    subject: str,
    body: str = ""
) -> Tuple[bool, str]:
    """
    Creates a mailto: link for the user's default email client.
    This function no longer directly sends emails but provides a link
    that can be opened to compose an email in the default client.
    
    Args:
        to_email: The recipient's email address
        subject: The email subject
        body: The email body text
        
    Returns:
        Tuple containing success flag and the mailto link or error message
    """
    try:
        mailto_link = create_mailto_link(to_email, subject, body)
        return True, mailto_link
    except Exception as e:
        return False, f"Failed to create mailto link: {str(e)}"

def extract_email_address(s: str) -> str:
    """Extract email address from a string containing potential formatting"""
    if not s:
        return ""
    match = re.search(r'[\w\.-]+@[\w\.-]+', s)
    return match.group(0).lower() if match else s.strip().lower()