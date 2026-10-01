"""Application bootstrap: idempotent startup sequence shared by all runtimes.

Called from the FastAPI lifespan (uvicorn/Docker) *and* at import time by the
Vercel serverless entrypoint, because serverless platforms do not always run
ASGI lifespan hooks. Every step is guarded so calling it twice is harmless.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.database import DB
from app.services.engine import ENGINE
from app.services.store import STORE

logger = logging.getLogger("cyberverse.bootstrap")

_state: dict[str, Any] = {"done": False}


def bootstrap() -> dict[str, Any]:
    if _state["done"]:
        return _state

    configure_logging()

    problems = settings.validate()
    for problem in problems:
        if settings.is_production:
            logger.error("configuration problem: %s", problem)
        else:
            logger.warning("configuration problem: %s", problem)
    if problems and settings.is_production:
        raise RuntimeError("Invalid configuration: " + "; ".join(problems))

    db_mode = DB.init(
        settings.database_url,
        autocreate=settings.db_autocreate,
        pool_size=settings.db_pool_size,
    )
    hydrated = STORE.hydrate()
    ENGINE.seed()
    if db_mode != "disabled" and DB.enabled:
        try:
            USERS = _users()
            USERS.purge_expired()
            admin = _seed_admin(USERS)
            if admin:
                logger.info("seeded admin account %s", admin["email"])
        except Exception:  # pragma: no cover - defensive
            logger.exception("admin bootstrap failed")

    _state.update(
        {
            "done": True,
            "database": db_mode,
            "hydrated": hydrated,
            "auth_active": settings.auth_active,
            "config_problems": problems,
        }
    )
    logger.info(
        "bootstrap complete",
        extra={
            "database": db_mode,
            "auth": settings.auth_active,
            "environment": settings.environment,
        },
    )
    return _state


def _users():
    from app.services.users import USERS

    return USERS


def _seed_admin(users) -> dict[str, Any] | None:
    """Create the initial administrator when credentials are configured."""
    if not settings.auth_active:
        return None
    email = settings.seed_admin_email.strip().lower()
    if users.get_by_email(email):
        return None
    if not settings.seed_admin_password:
        logger.warning(
            "AUTH is active but SEED_ADMIN_PASSWORD is unset - no admin account created"
        )
        return None
    user = users.create(
        email=email,
        password=settings.seed_admin_password,
        role="admin",
        full_name="Bootstrap Admin",
    )
    from app.services.audit import audit

    audit("user.seeded", user=user, resource=user["id"], detail={"bootstrap": True})
    return user
