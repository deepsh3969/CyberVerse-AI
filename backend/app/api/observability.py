"""Observability endpoints: Prometheus metrics and readiness probe."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Response

from app.api.ratelimit import rate_limit
from app.core.config import settings
from app.core.metrics import METRICS
from app.db.database import DB
from app.services.store import STORE

metrics_router = APIRouter(tags=["observability"])
ready_router = APIRouter(tags=["observability"])

STARTED_AT = time.time()

_READY_DEPENDENCIES = [Depends(rate_limit)]


@metrics_router.get("/metrics", dependencies=_READY_DEPENDENCIES)
def prometheus_metrics() -> Response:
    """Prometheus text exposition (scrape endpoint).

    Unauthenticated by default: most scrapers (Prometheus, Grafana Agent)
    sit on a private network. Set `METRICS_ENABLED=false` to disable, or
    front it with network policy / basic auth at the proxy.
    """
    if not settings.metrics_enabled:
        return Response(status_code=404, media_type="text/plain")
    METRICS.set_gauge("cyberverse_up", 1.0)
    METRICS.set_gauge(
        "cyberverse_database_info", 1.0, mode=DB.mode if DB.enabled else "disabled"
    )
    METRICS.set_gauge("cyberverse_auth_enabled", 1.0 if settings.auth_active else 0.0)
    METRICS.set_gauge("cyberverse_events_total", float(len(STORE.events)))
    METRICS.set_gauge("cyberverse_incidents_total", float(len(STORE.incidents)))
    METRICS.set_gauge("cyberverse_threats_total", float(len(STORE.threats)))
    METRICS.set_gauge("cyberverse_events_analyzed_total", float(STORE.events_analyzed))
    METRICS.set_gauge("cyberverse_security_score", float(STORE.security_score()))
    METRICS.set_gauge("cyberverse_uptime_seconds", float(time.time() - STARTED_AT))
    if DB.enabled:
        METRICS.set_gauge("cyberverse_audit_entries", float(DB.count("audit")))
    return Response(content=METRICS.render(), media_type="text/plain; version=0.0.4")


@ready_router.get("/ready", dependencies=_READY_DEPENDENCIES)
def readiness() -> Response:
    """Readiness probe: 200 when the process can serve traffic safely.

    - config: `settings.validate()` problems (fatal in production)
    - database: `SELECT 1` ping when `DATABASE_URL` is configured
      (an unset database is a valid demo configuration, reported as
      `disabled` rather than a failure)
    """
    import json

    checks: dict[str, dict] = {
        "config": {"status": "ok", "problems": settings.validate()},
        "database": {"status": "disabled"},
    }
    healthy = not checks["config"]["problems"]
    if DB.enabled:
        ok = DB.ping()
        checks["database"] = {
            "status": "ok" if ok else "error",
            "mode": DB.mode,
            "error": DB.error if not ok else None,
        }
        healthy = healthy and ok
    payload = {
        "status": "ready" if healthy else "degraded",
        "uptime_seconds": round(time.time() - STARTED_AT, 1),
        "database": DB.mode if DB.enabled else "disabled",
        "auth": settings.auth_active,
        "environment": settings.environment,
        "checks": checks,
    }
    return Response(
        content=json.dumps(payload),
        status_code=200 if healthy else 503,
        media_type="application/json",
    )
