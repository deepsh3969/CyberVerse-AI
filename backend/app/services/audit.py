"""Audit trail for security-relevant actions.

Every privileged action (login, containment, sandbox reset, user management)
is recorded with actor, action, resource, source IP and request id. Entries
are mirrored to the database when configured and always kept in a bounded
in-memory ring so the endpoint works in demo mode too.
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import deque
from typing import Any, Optional

from app.core.logging import request_id_var
from app.db.database import DB

logger = logging.getLogger("cyberverse.audit")

_RING: deque[dict[str, Any]] = deque(maxlen=1000)


def audit(
    action: str,
    *,
    user: Optional[dict[str, Any]] = None,
    resource: str = "",
    detail: Optional[dict[str, Any]] = None,
    ip: str = "",
) -> dict[str, Any]:
    entry = {
        "id": f"AUD-{uuid.uuid4().hex[:10].upper()}",
        "created_at": time.time(),
        "actor_id": (user or {}).get("id", ""),
        "actor_email": (user or {}).get("email", ""),
        "action": action,
        "resource": resource,
        "detail": detail or {},
        "ip": ip,
        "request_id": request_id_var.get(),
    }
    _RING.appendleft(entry)
    DB.write("audit", entry)
    logger.info(
        "audit",
        extra={"action": action, "resource": resource, "actor": entry["actor_email"]},
    )
    return entry


def recent(limit: int = 100) -> list[dict[str, Any]]:
    """Newest first. Database-backed when available, ring buffer otherwise."""
    if DB.enabled:
        rows = DB.load_audit(limit=limit)
        if rows:
            rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
            return rows
    return list(_RING)[:limit]
