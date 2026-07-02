from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import JWT_SECRET, JWT_TTL_HOURS

# bcrypt silently truncates passwords longer than 72 bytes instead of
# hashing the rest — reject oversized passwords instead of pretending
# they're fully used.
MAX_PASSWORD_BYTES = 72


class PasswordTooLong(ValueError):
    pass


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise PasswordTooLong(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
