"""User and refresh-token repository (PostgreSQL-backed).

Authentication is only active when both `AUTH_ENABLED=true` and `DATABASE_URL`
is configured (see `settings.auth_active`); production startup refuses the
combination where auth is requested without a database.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.security import AuthError, hash_password, hash_token, verify_password
from app.db.database import DB
from app.db.models import RefreshTokenRow, UserRow

logger = logging.getLogger("cyberverse.auth")

ROLES = ("viewer", "analyst", "admin")
ROLE_RANK = {role: idx for idx, role in enumerate(ROLES)}


def role_at_least(role: str, required: str) -> bool:
    return ROLE_RANK.get(role, -1) >= ROLE_RANK.get(required, 99)


def _user_dict(row: UserRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "role": row.role,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
    }


class UserRepository:
    def __init__(self) -> None:
        self._memory_users: dict[str, dict[str, Any]] = {}
        self._memory_tokens: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ users
    def get(self, user_id: str) -> Optional[dict[str, Any]]:
        if not DB.enabled:
            return self._memory_users.get(user_id)
        with DB.session() as session:
            row = session.get(UserRow, user_id)
            return _user_dict(row) if row else None

    def get_by_email(self, email: str) -> Optional[dict[str, Any]]:
        email = email.strip().lower()
        if not DB.enabled:
            for user in self._memory_users.values():
                if user["email"] == email:
                    return user
            return None
        with DB.session() as session:
            row = session.execute(select(UserRow).where(UserRow.email == email)).scalar_one_or_none()
            return _user_dict(row) if row else None

    def get_credentials(self, email: str) -> Optional[dict[str, Any]]:
        """Return the row needed for password verification."""
        email = email.strip().lower()
        if not DB.enabled:
            user = self.get_by_email(email)
            if user:
                return {**user, "password_hash": user.get("password_hash", "")}
            return None
        with DB.session() as session:
            row = session.execute(select(UserRow).where(UserRow.email == email)).scalar_one_or_none()
            if not row:
                return None
            return {**_user_dict(row), "password_hash": row.password_hash}

    def list(self) -> list[dict[str, Any]]:
        if not DB.enabled:
            return sorted(self._memory_users.values(), key=lambda u: u["email"])
        with DB.session() as session:
            rows = session.execute(select(UserRow).order_by(UserRow.email)).scalars().all()
            return [_user_dict(r) for r in rows]

    def create(
        self,
        *,
        email: str,
        password: str,
        role: str = "analyst",
        full_name: str = "",
        is_active: bool = True,
    ) -> dict[str, Any]:
        email = email.strip().lower()
        if role not in ROLES:
            raise AuthError(f"Invalid role '{role}'")
        if self.get_by_email(email):
            raise AuthError("A user with this email already exists", status=409)
        password_hash = hash_password(password)
        user_id = f"USR-{uuid.uuid4().hex[:10].upper()}"
        if not DB.enabled:
            user = {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": role,
                "is_active": is_active,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_login_at": None,
                "password_hash": password_hash,
            }
            self._memory_users[user_id] = user
            return {k: v for k, v in user.items() if k != "password_hash"}
        with DB.session() as session:
            row = UserRow(
                id=user_id,
                email=email,
                full_name=full_name,
                role=role,
                password_hash=password_hash,
                is_active=is_active,
            )
            session.add(row)
            session.flush()
            return _user_dict(row)

    def update(self, user_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        allowed = {"full_name", "role", "is_active"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if "role" in updates and updates["role"] not in ROLES:
            raise AuthError(f"Invalid role '{updates['role']}'")
        if not updates:
            return self.get(user_id)
        if not DB.enabled:
            user = self._memory_users.get(user_id)
            if not user:
                return None
            user.update(updates)
            return {k: v for k, v in user.items() if k != "password_hash"}
        with DB.session() as session:
            row = session.get(UserRow, user_id)
            if not row:
                return None
            for key, value in updates.items():
                setattr(row, key, value)
            session.flush()
            return _user_dict(row)

    def set_password(self, user_id: str, password: str) -> Optional[dict[str, Any]]:
        password_hash = hash_password(password)
        if not DB.enabled:
            user = self._memory_users.get(user_id)
            if not user:
                return None
            user["password_hash"] = password_hash
            return {k: v for k, v in user.items() if k != "password_hash"}
        with DB.session() as session:
            row = session.get(UserRow, user_id)
            if not row:
                return None
            row.password_hash = password_hash
            session.flush()
            return _user_dict(row)

    def check_password(self, email: str, password: str) -> Optional[dict[str, Any]]:
        """Return the user dict when credentials are valid, else None."""
        creds = self.get_credentials(email)
        if not creds or not creds.get("is_active", True):
            return None
        if not verify_password(password, creds["password_hash"]):
            return None
        return {k: v for k, v in creds.items() if k != "password_hash"}

    def record_login(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        if not DB.enabled:
            user = self._memory_users.get(user_id)
            if user:
                user["last_login_at"] = now.isoformat()
            return
        with DB.session() as session:
            row = session.get(UserRow, user_id)
            if row:
                row.last_login_at = now

    def delete(self, user_id: str) -> bool:
        if not DB.enabled:
            return self._memory_users.pop(user_id, None) is not None
        with DB.session() as session:
            row = session.get(UserRow, user_id)
            if not row:
                return False
            session.delete(row)
            return True

    # -------------------------------------------------------- refresh tokens
    def issue_refresh_token(self, user_id: str, user_agent: str = "") -> str:
        raw, token_hash, expires_at = _issue()
        if DB.enabled:
            with DB.session() as session:
                session.add(
                    RefreshTokenRow(
                        id=f"RT-{uuid.uuid4().hex[:12].upper()}",
                        user_id=user_id,
                        token_hash=token_hash,
                        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
                        user_agent=user_agent[:255],
                    )
                )
        else:  # pragma: no cover - demo mode without a database
            self._memory_tokens[token_hash] = {
                "user_id": user_id,
                "expires_at": expires_at,
            }
        return raw

    def consume_refresh_token(self, raw: str) -> Optional[str]:
        """Validate + revoke a refresh token. Returns the user id when valid."""
        token_hash = hash_token(raw)
        now = datetime.now(timezone.utc)
        if not DB.enabled:  # pragma: no cover - demo mode without a database
            entry = self._memory_tokens.pop(token_hash, None)
            if not entry or entry["expires_at"] < time.time():
                return None
            return entry["user_id"]
        with DB.session() as session:
            row = session.execute(
                select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
            ).scalar_one_or_none()
            if not row or row.revoked_at is not None:
                return None
            expires = row.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                return None
            user_id = row.user_id
            row.revoked_at = now
            return user_id

    def revoke_all_for_user(self, user_id: str) -> int:
        now = datetime.now(timezone.utc)
        if not DB.enabled:  # pragma: no cover
            stale = [h for h, e in self._memory_tokens.items() if e["user_id"] == user_id]
            for h in stale:
                self._memory_tokens.pop(h, None)
            return len(stale)
        with DB.session() as session:
            rows = (
                session.execute(
                    select(RefreshTokenRow).where(
                        RefreshTokenRow.user_id == user_id,
                        RefreshTokenRow.revoked_at.is_(None),
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                row.revoked_at = now
            return len(rows)

    def purge_expired(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        if not DB.enabled:  # pragma: no cover
            before = len(self._memory_tokens)
            self._memory_tokens = {
                h: e for h, e in self._memory_tokens.items() if e["expires_at"] > time.time()
            }
            return before - len(self._memory_tokens)
        with DB.session() as session:
            rows = (
                session.execute(
                    select(RefreshTokenRow).where(
                        RefreshTokenRow.revoked_at.is_not(None),
                        RefreshTokenRow.created_at < cutoff,
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                session.delete(row)
            return len(rows)


def _issue() -> tuple[str, str, int]:
    from app.core.security import new_refresh_token

    return new_refresh_token()


USERS = UserRepository()
