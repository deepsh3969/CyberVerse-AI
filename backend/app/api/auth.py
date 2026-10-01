"""Authentication, session and user-management endpoints."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import require_role, require_user
from app.api.ratelimit import client_ip, rate_limit_login
from app.core.config import settings
from app.core.security import (
    AuthError,
    create_access_token,
    validate_password,
)
from app.services.audit import audit, recent as audit_recent
from app.services.users import ROLES, USERS

logger = logging.getLogger("cyberverse.auth")

auth_router = APIRouter(prefix="/auth", tags=["auth"])
audit_router = APIRouter(tags=["audit"])

REFRESH_COOKIE = "cv_rt"
REFRESH_COOKIE_PATH = "/api/auth"


# --------------------------------------------------------------------- models
class LoginBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class CreateUserBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="analyst")
    full_name: str = Field(default="", max_length=120)


class UpdateUserBody(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = Field(default=None, max_length=120)


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.refresh_token_ttl,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.cookies_secure,
    )


def _auth_disabled() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail="Authentication is disabled in this deployment (demo mode)",
    )


# ---------------------------------------------------------------------- login
@auth_router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    rate_limit_login(request)
    if not settings.auth_active:
        raise _auth_disabled()
    ip = client_ip(request)
    user = USERS.check_password(body.email, body.password)
    if not user:
        audit(
            "auth.login.failed",
            resource=body.email.lower(),
            detail={"reason": "invalid credentials"},
            ip=ip,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access = create_access_token(user_id=user["id"], email=user["email"], role=user["role"])
    refresh = USERS.issue_refresh_token(user["id"], request.headers.get("user-agent", ""))
    USERS.record_login(user["id"])
    _set_refresh_cookie(response, refresh)
    audit("auth.login", user=user, ip=ip)
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl,
        "user": user,
    }


@auth_router.post("/refresh")
def refresh(request: Request, response: Response) -> dict[str, Any]:
    if not settings.auth_active:
        raise _auth_disabled()
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="No refresh token")
    user_id = USERS.consume_refresh_token(raw)
    if not user_id:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token revoked or expired")
    user = USERS.get(user_id)
    if not user or not user.get("is_active", True):
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Account disabled")
    access = create_access_token(user_id=user["id"], email=user["email"], role=user["role"])
    rotated = USERS.issue_refresh_token(user["id"], request.headers.get("user-agent", ""))
    _set_refresh_cookie(response, rotated)
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": settings.access_token_ttl,
        "user": user,
    }


@auth_router.post("/logout")
def logout(request: Request, response: Response) -> dict[str, Any]:
    raw = request.cookies.get(REFRESH_COOKIE)
    user_id = USERS.consume_refresh_token(raw) if raw else None
    _clear_refresh_cookie(response)
    if settings.auth_active and user_id:
        user = USERS.get(user_id)
        if user:
            audit("auth.logout", user=user, ip=client_ip(request))
    return {"status": "ok"}


@auth_router.get("/me")
def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"user": user}


@auth_router.post("/password")
def change_password(
    body: ChangePasswordBody,
    request: Request,
    response: Response,
    user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if not settings.auth_active:
        raise _auth_disabled()
    if user.get("id") == "anonymous":
        raise HTTPException(status_code=403, detail="Anonymous operators cannot change passwords")
    try:
        validate_password(body.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    verified = USERS.check_password(user["email"], body.current_password)
    if not verified:
        audit("auth.password.failed", user=user, ip=client_ip(request))
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    USERS.set_password(user["id"], body.new_password)
    revoked = USERS.revoke_all_for_user(user["id"])
    _clear_refresh_cookie(response)
    audit("auth.password.changed", user=user, detail={"sessions_revoked": revoked}, ip=client_ip(request))
    return {"status": "password updated", "sessions_revoked": revoked}


# ------------------------------------------------------------- user management
@auth_router.get("/users")
def list_users(admin: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    return {"items": USERS.list(), "total": len(USERS.list())}


@auth_router.post("/users", status_code=201)
def create_user(
    body: CreateUserBody,
    request: Request,
    admin: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    if body.role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Role must be one of {', '.join(ROLES)}")
    try:
        user = USERS.create(
            email=body.email,
            password=body.password,
            role=body.role,
            full_name=body.full_name,
        )
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
    audit(
        "user.created",
        user=admin,
        resource=user["id"],
        detail={"email": user["email"], "role": user["role"]},
        ip=client_ip(request),
    )
    return {"user": user}


@auth_router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UpdateUserBody,
    request: Request,
    admin: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if body.role is not None:
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.full_name is not None:
        updates["full_name"] = body.full_name
    try:
        user = USERS.update(user_id, **updates)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == admin.get("id") and (updates.get("is_active") is False or updates.get("role") != "admin"):
        # Undo self-demotion/self-lockout: an admin must not lock themselves out.
        USERS.update(user_id, role="admin", is_active=True)
        raise HTTPException(status_code=409, detail="You cannot demote or disable your own account")
    audit(
        "user.updated",
        user=admin,
        resource=user_id,
        detail=updates,
        ip=client_ip(request),
    )
    return {"user": USERS.get(user_id)}


@auth_router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    request: Request,
    admin: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    if user_id == admin.get("id"):
        raise HTTPException(status_code=409, detail="You cannot delete your own account")
    deleted = USERS.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    audit("user.deleted", user=admin, resource=user_id, ip=client_ip(request))
    return {"status": "deleted", "id": user_id}


# ------------------------------------------------------------------------ audit
@audit_router.get("/audit")
def list_audit(
    limit: int = 100,
    admin: dict[str, Any] = Depends(require_role("admin")),
) -> dict[str, Any]:
    items = audit_recent(limit=max(1, min(limit, 500)))
    return {"items": items, "total": len(items)}
