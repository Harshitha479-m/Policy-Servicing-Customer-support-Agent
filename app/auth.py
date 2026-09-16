from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class User:
    username: str
    role: str


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str, expected_username: str, expected_password: str) -> User | None:
    if hmac.compare_digest(username, expected_username) and hmac.compare_digest(password, expected_password):
        return User(username=username, role="read_only_service")
    return None


def session_is_valid(created_at: datetime, ttl_minutes: int) -> bool:
    now = datetime.now(timezone.utc)
    return now - created_at < timedelta(minutes=ttl_minutes)
