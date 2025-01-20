import os
import base64
from cryptography.fernet import Fernet

# 1) For demonstration, you can do something like:
#    encryption_key = os.environ.get("MYAPP_CRYPTO_KEY", None)
#    If key is None, fallback to a hardcoded key or generate.

# Hardcoding a key for illustration (NOT for production):
HARDCODED_KEY = b'8VOoJFX2_4HPY4uw8N1-4qrNdZtEm_-9l_ezrnu16o4='  
# This should be a 32-byte URL-safe base64-encoded key, exactly what Fernet expects.

def get_fernet_key() -> bytes:
    """
    Returns a 32-byte URL-safe base64 key for Fernet.
    In production, read from a secure location (env variable, vault, etc.).
    """
    key = os.environ.get("MYAPP_CRYPTO_KEY", "")
    if key:
        return key.encode("utf-8")  # from string to bytes
    else:
        return HARDCODED_KEY  # fallback

def encrypt_value(plaintext: str) -> str:
    """
    Encrypts the plaintext using Fernet, returns a Base64-encoded ciphertext string.
    """
    if not plaintext:
        return ""
    f = Fernet(get_fernet_key())
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")  # store as string

def decrypt_value(ciphertext: str) -> str:
    """
    Decrypts the ciphertext (Base64-encoded) using Fernet, returns plaintext.
    If anything goes wrong (e.g., empty or invalid ciphertext), return empty string.
    """
    if not ciphertext:
        return ""
    try:
        f = Fernet(get_fernet_key())
        plaintext_bytes = f.decrypt(ciphertext.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")
    except Exception:
        return ""
