from PyQt6.QtCore import QSettings
from .crypto_service import encrypt_value, decrypt_value

ORGANIZATION_NAME = "MyCompany"
APPLICATION_NAME = "MySmartApp"

def get_qsettings() -> QSettings:
    return QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

def get_linkedin_url() -> str:
    settings = get_qsettings()
    return settings.value("user/linkedin_url", "", type=str)

def set_linkedin_url(url: str):
    settings = get_qsettings()
    settings.setValue("user/linkedin_url", url)
    settings.sync()

def get_resume_folder() -> str:
    settings = get_qsettings()
    return settings.value("user/resume_folder", "", type=str)

def set_resume_folder(folder: str):
    settings = get_qsettings()
    settings.setValue("user/resume_folder", folder)
    settings.sync()

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