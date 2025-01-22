import os
from PyQt6.QtCore import QSettings
from .crypto_service import encrypt_value, decrypt_value
from transformations.wiza_transformation import WizaAPI
import PyPDF2
import docx2txt

# For .env handling
from dotenv import load_dotenv, set_key, get_key

ORGANIZATION_NAME = "MyCompany"
APPLICATION_NAME = "MySmartApp"
ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

def get_qsettings() -> QSettings:
    return QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

# -------------------------------
# Resume and User Info Functions
# -------------------------------

def parse_pdf_resume(file_path):
    """Parse PDF resume into text"""
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def parse_docx_resume(file_path):
    """Parse DOCX resume into text"""
    doc = docx2txt.process(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def save_user_resume(file_path):
    """Save parsed resume to text file"""
    if not file_path:
        return
        
    if file_path.endswith('.pdf'):
        text = parse_pdf_resume(file_path)
    elif file_path.endswith('.docx'):
        text = parse_docx_resume(file_path)
    else:
        raise ValueError("Unsupported file format")
    
    with open('user_resume.txt', 'w', encoding='utf-8') as f:
        f.write(text)

def save_user_info(linkedin_url):
    """Save Wiza profile data to text file"""
    if not linkedin_url:
        return
        
    try:
        wiza = WizaAPI()
        data = wiza.get_profile_data(linkedin_url)
        
        with open('user_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(data))
    except Exception as e:
        print(f"Error saving user info: {e}")

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

def get_resume_path() -> str:
    settings = get_qsettings()
    return settings.value("user/resume_path", "", type=str)

def set_resume_path(path: str):
    settings = get_qsettings()
    settings.setValue("user/resume_path", path)
    settings.sync()
    save_user_resume(path)  # Automatically parse and save resume

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