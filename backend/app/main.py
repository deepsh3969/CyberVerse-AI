"""CyberVerse AI - FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.auth import audit_router, auth_router
from app.api.observability import metrics_router, ready_router
from app.api.ratelimit import rate_limit
from app.api.routes import router
from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.middleware import RequestContextMiddleware
from app.services.engine import ENGINE


def _find_dist() -> Path | None:
    """Locate the built frontend, if one exists (repo layout or CWD)."""
    repo_root = Path(__file__).resolve().parents[2]
    for candidate in (
        repo_root / "frontend" / "dist",
        Path.cwd() / "frontend" / "dist",
        Path.cwd() / "dist",
    ):
        if candidate.is_dir():
            return candidate
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield


app = FastAPI(
    title="CyberVerse AI API",
    description="AI-powered 3D cybersecurity command center backend (simulated telemetry only).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    # Required for the HttpOnly refresh cookie when the console and the API
    # are served from different origins (always false on the Vercel build).
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)
# Outermost: correlation id, access log, metrics, security headers, body cap.
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


@app.get("/", tags=["meta"], response_model=None)
def root() -> JSONResponse | HTMLResponse:
    """Serve the SPA landing page when a build exists, else service metadata."""
    dist = _find_dist()
    index = dist / "index.html" if dist else None
    if index is not None and index.is_file():
        return HTMLResponse(
            index.read_text(encoding="utf-8"),
            headers={"Cache-Control": "public, max-age=60"},
        )
    return JSONResponse(
        {
            "name": settings.app_name,
            "tagline": "SEE THE ATTACK. UNDERSTAND THE THREAT. STOP IT.",
            "docs": "/docs",
            "health": "/api/health",
            "mode": "simulated-sandbox",
        }
    )


app.include_router(router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix, dependencies=[Depends(rate_limit)])
app.include_router(audit_router, prefix=settings.api_prefix, dependencies=[Depends(rate_limit)])
app.include_router(ready_router, prefix=settings.api_prefix)
app.include_router(metrics_router)


def _register_frontend() -> None:
    """Serve the built SPA (same origin) when a build output is present.

    API path operations always win over frontend files, and unknown
    navigation requests fall back to ``index.html`` so client-side routes
    such as ``/app/incidents/INC-1`` work when opened directly.
    """
    if not hasattr(app, "frontend"):
        return
    dist = _find_dist()
    if dist is None:
        return
    try:
        relative = dist.relative_to(Path.cwd())
    except ValueError:
        directory = str(dist)
    else:
        directory = relative.as_posix()
    app.frontend("/", directory=directory, fallback="index.html", check_dir=False)


_register_frontend()
