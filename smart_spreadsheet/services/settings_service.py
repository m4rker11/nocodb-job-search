import os
import json
from PyQt6.QtCore import QSettings
from .crypto_service import encrypt_value, decrypt_value
from transformations.wiza_transformation import WizaAPI
from transformations.llm_transformation import MultiLLMTransformation

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
        data = wiza.get_profile_data(linkedin_url)
        
        with open('user_info.txt', 'w', encoding='utf-8') as f:
            f.write(str(data))
    except Exception as e:
        print(f"Error saving user info: {e}")

def ensure_resume_json_exists():
    """Ensure resume.json exists by converting from resume.txt if needed"""
    json_path = os.path.join(os.path.dirname(__file__), "resume.json")
    
    if not os.path.exists(json_path):
        resume_text = get_resume_text()
        if not resume_text:
            return False
            
        try:
            # Create LLM transformation instance
            llm = MultiLLMTransformation()
            
            # Load JSON schema
            schema_path = os.path.join(os.path.dirname(__file__), "resumeJSONSchema.json")
            with open(schema_path, "r", encoding="utf-8") as f:
                resume_format = f.read()
            
            # Prepare prompts
            system_prompt = "You are a resume parsing expert."
            user_prompt = (
                "Convert this text extracted from my resume to resumeJSON.\n"
                "----MY RESUME TEXT----\n{text}\n----------------------\n"
                "Respond with it in the following JSON format:\n"
                "----RESUME JSON FORMAT----\n{format}\n--------------------------\n"
                "Rules:\n"
                "1. If there is no information matching the field or it's not in the right format "
                "(e.g. date in YYYY-MM-DD), don't include the field.\n"
                "2. You MUST respond with the entire field's text if it is in the right format.\n"
                "3. Conform the existing information to the JSON format, to make sure as much information as possible is included.\n"
                "Respond with just the JSON."
            ).format(text=resume_text, format=resume_format)
            
            # Call LLM
            resume_json_str = llm._call_llm(
                provider="openai",
                model_name="gpt-4o-mini",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True
            )
            
            # Save JSON
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(resume_json_str)
                
            return True
            
        except Exception as e:
            print(f"Error converting resume to JSON: {e}")
            return False
    
    return True

def save_user_resume(resume_text):
    """Save resume text to file and update JSON"""
    # Save to text file
    with open('user_resume.txt', 'w', encoding='utf-8') as f:
        f.write(resume_text)
    
    # Force regeneration of JSON
    json_path = os.path.join(os.path.dirname(__file__), "resume.json")
    if os.path.exists(json_path):
        os.remove(json_path)
    
    # Generate new JSON
    ensure_resume_json_exists()

def get_resume_json():
    """Get the resume JSON data, converting from text if needed"""
    if ensure_resume_json_exists():
        json_path = os.path.join(os.path.dirname(__file__), "resume.json")
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

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