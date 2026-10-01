"""Shared test configuration.

The default suite runs with authentication disabled (demo mode) so the
scenario/detection tests stay readable. `auth_client` flips auth on against
a throwaway SQLite database and restores every setting it touches.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Must happen before any `app.*` import: config reads these at import time.
os.environ["AUTH_ENABLED"] = "false"
os.environ.pop("DATABASE_URL", None)

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_rate_buckets():
    from app.api.ratelimit import reset_buckets

    reset_buckets()
    yield
    reset_buckets()


@pytest.fixture()
def auth_client():
    """TestClient with auth active on a fresh SQLite database."""
    from fastapi.testclient import TestClient

    from app.bootstrap import _seed_admin, _users
    from app.core.config import settings
    from app.db.database import DB
    from app.services.users import USERS

    tmp = Path(tempfile.mkdtemp(prefix="cv-test-"))
    url = f"sqlite:///{tmp / 'auth.db'}"

    previous = {
        "auth_enabled": settings.auth_enabled,
        "auth_require_read": settings.auth_require_read,
        "database_url": settings.database_url,
        "seed_password": settings.seed_admin_password,
        "seed_email": settings.seed_admin_email,
        "jwt_secret": settings.jwt_secret,
        "ephemeral": settings._ephemeral_secret,
        "bcrypt_rounds": settings.bcrypt_rounds,
        "login_limit": settings.auth_login_limit_per_minute,
    }
    settings.auth_enabled = True
    settings.auth_require_read = False
    settings.database_url = url
    settings.seed_admin_email = "admin@cyberverse.local"
    settings.seed_admin_password = "AdminPass123!"
    settings.jwt_secret = "test-secret-test-secret-test-secret-32"
    settings._ephemeral_secret = False
    settings.bcrypt_rounds = 4  # fast tests; production default is 12
    settings.auth_login_limit_per_minute = 0  # disabled unless a test opts in

    DB.init(url, autocreate=True)
    _seed_admin(_users())

    from app.main import app

    with TestClient(app) as client:
        yield client

    DB.close()
    DB.mode = "disabled"
    DB.error = None
    settings.auth_enabled = previous["auth_enabled"]
    settings.auth_require_read = previous["auth_require_read"]
    settings.database_url = previous["database_url"]
    settings.seed_admin_password = previous["seed_password"]
    settings.seed_admin_email = previous["seed_email"]
    settings.jwt_secret = previous["jwt_secret"]
    settings._ephemeral_secret = previous["ephemeral"]
    settings.bcrypt_rounds = previous["bcrypt_rounds"]
    settings.auth_login_limit_per_minute = previous["login_limit"]
    USERS._memory_users.clear()
    USERS._memory_tokens.clear()


@pytest.fixture()
def admin_login(auth_client):
    """Convenience: returns (client, headers, user) for the seeded admin."""
    resp = auth_client.post(
        "/api/auth/login",
        json={"email": "admin@cyberverse.local", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return auth_client, {"Authorization": f"Bearer {token}"}, resp.json()["user"]
