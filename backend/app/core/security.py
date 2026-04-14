import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from cryptography.fernet import Fernet

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours for admin sessions


# ── Password hashing (bcrypt directly — avoids passlib/bcrypt compat issues) ─

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT (admin auth) ──────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── OTP generation ────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


# ── Fernet symmetric encryption (data packages) ───────────────────────────────

def get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        # Auto-generate a key in dev — warn loudly
        key = Fernet.generate_key().decode()
        import logging
        logging.getLogger(__name__).warning(
            "ENCRYPTION_KEY not set — generated ephemeral key. "
            "Set ENCRYPTION_KEY in .env for persistent encryption."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_data(data: bytes) -> bytes:
    return get_fernet().encrypt(data)


def decrypt_data(token: bytes) -> bytes:
    return get_fernet().decrypt(token)
