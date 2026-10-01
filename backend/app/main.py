"""CyberVerse AI - FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.services.engine import ENGINE


@asynccontextmanager
async def lifespan(app: FastAPI):
    ENGINE.seed()
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


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


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "tagline": "SEE THE ATTACK. UNDERSTAND THE THREAT. STOP IT.",
        "docs": "/docs",
        "health": "/api/health",
        "mode": "simulated-sandbox",
    }


app.include_router(router, prefix=settings.api_prefix)
