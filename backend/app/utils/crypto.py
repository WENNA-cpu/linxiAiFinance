from cryptography.fernet import Fernet
import hashlib
import base64
import os

SECRET_KEY = os.getenv("SECRET_KEY", Fernet.generate_key())
cipher_suite = Fernet(SECRET_KEY)


def encrypt_data(data: str) -> str:
    """AES-256加密"""
    encrypted = cipher_suite.encrypt(data.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_data(encrypted_data: str) -> str:
    """AES-256解密"""
    decrypted = cipher_suite.decrypt(base64.b64decode(encrypted_data))
    return decrypted.decode()


def hash_data(data: str) -> str:
    """SHA256哈希"""
    return hashlib.sha256(data.encode()).hexdigest()
