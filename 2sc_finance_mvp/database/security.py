from cryptography.fernet import Fernet
import os

# In production, store this in your .env
ENCRYPTION_KEY = os.getenv("FILE_ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_file(file_bytes):
    return cipher.encrypt(file_bytes)

def decrypt_file(encrypted_bytes):
    return cipher.decrypt(encrypted_bytes)