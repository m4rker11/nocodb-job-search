import os
from PyQt6.QtCore import QSettings
from .crypto_service import encrypt_value, decrypt_value
from transformations.wiza_transformation import WizaAPI

# For .env handling
from dotenv import load_dotenv, set_key, get_key

ORGANIZATION_NAME = "MyCompany"
APPLICATION_NAME = "MySmartApp"
ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

def get_qsettings() -> QSettings:
    return QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

# -------------------------------
# User Info Functions
# -------------------------------

def save_user_info(linkedin_url):
    """Save Wiza profile data to text file"""
    if not linkedin_url:
        return
        
    try:
        wiza = WizaAPI()
        reveal_id = wiza.create_individual_reveal(linkedin_url)
        data = wiza.get_individual_reveal(reveal_id)
        
        with open('user_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(data))
    except Exception as e:
        print(f"Error saving user info: {e}")

def save_user_resume(resume_text):
    """Save resume text to file"""
    with open('user_resume.txt', 'w', encoding='utf-8') as f:
        f.write(resume_text)

# -------------------------------
# QSETTINGS-BASED FUNCTIONS
# -------------------------------

def get_linkedin_url() -> str:
    settings = get_qsettings()
    return settings.value("user/linkedin_url", "", type=str)

def set_linkedin_url(url: str):
    settings = get_qsettings()
    settings.setValue("user/linkedin_url", url)
    settings.sync()
    save_user_info(url)  # Automatically trigger Wiza save

def get_resume_text() -> str:
    settings = get_qsettings()
    return settings.value("user/resume_text", "", type=str)

def set_resume_text(text: str):
    settings = get_qsettings()
    settings.setValue("user/resume_text", text)
    settings.sync()
    save_user_resume(text)  # Automatically save resume text

def get_email_account() -> str:
    settings = get_qsettings()
    return settings.value("email/account", "", type=str)

def set_email_account(account: str):
    settings = get_qsettings()
    settings.setValue("email/account", account)
    settings.sync()

def get_email_password() -> str:
    settings = get_qsettings()
    encrypted = settings.value("email/password", "", type=str)
    return decrypt_value(encrypted)

def set_email_password(password: str):
    settings = get_qsettings()
    encrypted = encrypt_value(password)
    settings.setValue("email/password", encrypted)
    settings.sync()

# -------------------------------
# ENV (.env) FUNCTIONS
# -------------------------------

def load_env_vars():
    """Load existing .env variables into os.environ"""
    load_dotenv(ENV_FILE_PATH)

def get_env_var(key: str) -> str:
    """Get value from .env file or environment"""
    return get_key(ENV_FILE_PATH, key) or ""

def set_env_var(key: str, value: str):
    """Write/update a key in the .env file"""
    if not os.path.exists(ENV_FILE_PATH):
        with open(ENV_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("")
    set_key(ENV_FILE_PATH, key, value)