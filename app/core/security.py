from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from typing import Any

import jwt

from app.core.clock import utcnow
from app.core.errors import AppError

_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_access_token(secret: str, user_id: int, role: str, ttl_minutes: int) -> str:
    now = utcnow()
    claims = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=ttl_minutes)}
    return jwt.encode(claims, secret, algorithm=_ALGORITHM)


def decode_access_token(secret: str, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise AppError("auth.invalid_token", 401) from exc


def random_pin() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def random_token() -> str:
    return secrets.token_urlsafe(24)
