import hashlib
import os

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, hashed = password_hash.split(":")
        check = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return check == hashed
    except Exception:
        return False
