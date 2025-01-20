# services/email_service.py

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from services.settings_service import (
    get_email_account,
    get_email_password
)

def send_email_smtp(
    to_email: str,
    subject: str,
    body: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587
):
    """
    Fetch sender email + password from QSettings, then send the message to `to_email`.
    """
    sender_email = get_email_account()       # e.g. "mygmail@gmail.com"
    sender_password = get_email_password()   # decrypted automatically
    if not sender_email or not sender_password:
        return False, "Missing email account or password in Settings."

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
