"""Password hashing and JWT issuing/verification.

- Passwords: bcrypt (cost configurable via BCRYPT_ROUNDS).
- Access tokens: short-lived JWTs (HS256) carrying `sub`, `email`, `role`.
- Refresh tokens: opaque random strings, stored **hashed** (SHA-256) in the
  database and delivered to the browser in an HttpOnly cookie; rotation on
  every refresh, revocation on logout/password change.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt limit


class AuthError(Exception):
    """Authentication/authorization failure carrying an HTTP status."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AuthError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


# --------------------------------------------------------------------- tokens
def create_access_token(*, user_id: str, email: str, role: str) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + settings.access_token_ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def new_refresh_token() -> tuple[str, str, int]:
    """Return ``(raw_token, sha256_hash, expires_at_epoch)``."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw), int(time.time()) + settings.refresh_token_ttl


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
