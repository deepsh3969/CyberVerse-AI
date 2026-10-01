"""Vercel serverless entrypoint.

Routes every ``/api/*`` request to the FastAPI application living in
``backend/app``. The frontend is served from ``frontend/dist`` by the same
deployment, so the console and the API share one origin and no CORS or
``VITE_API_URL`` configuration is needed.

Only synthetic, simulated telemetry is produced by this service.
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
for _path in (REPO_ROOT, BACKEND_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from app.main import app as fastapi_app  # noqa: E402
from app.services.engine import ENGINE  # noqa: E402

# The serverless runtime does not always execute ASGI lifespan hooks, and the
# operation is idempotent (STORE.seeded guard), so seed at import time too.
ENGINE.seed()

# First path segments that belong to the API. Used only to repair a runtime
# that strips the ``/api`` prefix; everything else (``/``, ``/assets/*``,
# ``/app/*``) must reach the application untouched so the SPA is served.
API_SEGMENTS = frozenset(
    {
        "health",
        "dashboard",
        "network",
        "events",
        "threats",
        "incidents",
        "attack-graph",
        "scenarios",
        "simulate",
        "analyze",
        "reports",
        "demo",
        "settings",
        "reset",
    }
)


class PathNormalizer:
    """Re-prefix ``/api`` only when a stripped API path is detected."""

    def __init__(self, inner) -> None:
        self.inner = inner

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http":
            path = scope.get("path") or "/"
            first = path.lstrip("/").split("/", 1)[0]
            if first in API_SEGMENTS and not path.startswith("/api"):
                normalized = "/api" + (path if path.startswith("/") else "/" + path)
                scope = dict(scope)
                scope["path"] = normalized
                scope["raw_path"] = normalized.encode("utf-8")
        await self.inner(scope, receive, send)


app = PathNormalizer(fastapi_app)
