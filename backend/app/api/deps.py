"""FastAPI dependencies: authentication and RBAC.

Behaviour matrix
----------------
* `AUTH_ENABLED=false` or no `DATABASE_URL` -> the API runs open (demo mode);
  `require_user` yields an anonymous admin so scripted demos keep working.
  Production startup refuses auth-without-database (see `settings.validate`).
* reads  -> open unless `AUTH_REQUIRE_READ=true`
* writes -> authenticated (`analyst` or `admin`)
* user management / audit / sandbox reset -> `admin`
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request

from app.core.config import settings
from app.core.security import decode_access_token
from app.services.users import USERS, role_at_least

ANONYMOUS_USER: dict[str, Any] = {
    "id": "anonymous",
    "email": "local@cyberverse",
    "full_name": "Local demo operator",
    "role": "admin",
    "is_active": True,
}


def _bearer(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header[:7].lower() == "bearer ":
        return header[7:].strip() or None
    return None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_optional_user(request: Request) -> Optional[dict[str, Any]]:
    """Valid token -> user dict; no token -> None; bad token -> 401."""
    if not settings.auth_active:
        return None
    token = _bearer(request)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        raise _unauthorized("Invalid or expired access token")
    user = USERS.get(str(payload.get("sub", "")))
    if not user or not user.get("is_active", True):
        raise _unauthorized("Account disabled or unknown")
    return user


def require_user(request: Request) -> dict[str, Any]:
    if not settings.auth_active:
        return ANONYMOUS_USER
    user = get_optional_user(request)
    if not user:
        raise _unauthorized("Authentication required")
    return user


def require_read(request: Request, user: Optional[dict[str, Any]] = Depends(get_optional_user)) -> dict[str, Any]:
    if not settings.auth_active or not settings.auth_require_read:
        return user or ANONYMOUS_USER
    if not user:
        raise _unauthorized("Authentication required")
    return user


def require_role(min_role: str) -> Callable[..., dict[str, Any]]:
    def dependency(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
        if not settings.auth_active:
            return user
        if not role_at_least(str(user.get("role", "viewer")), min_role):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{min_role}' or higher is required",
            )
        return user

    return dependency
