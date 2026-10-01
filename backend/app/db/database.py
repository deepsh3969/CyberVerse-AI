"""Durable storage (PostgreSQL in production, SQLite in tests).

The API works with `DATABASE_URL` unset (in-memory demo mode). When a URL is
configured the store is hydrated at startup and every mutation is mirrored
with best-effort write-through semantics: a storage hiccup is logged and
degrades the mode, it never breaks a request.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    AttackGraphRow,
    AuditLogRow,
    Base,
    EventRow,
    IncidentRow,
    ThreatRow,
)

logger = logging.getLogger("cyberverse.db")

# collection name -> (model, id field)
_COLLECTIONS: dict[str, tuple[type, str]] = {
    "events": (EventRow, "id"),
    "threats": (ThreatRow, "id"),
    "incidents": (IncidentRow, "id"),
    "attack_paths": (AttackGraphRow, "incident_id"),
    "audit": (AuditLogRow, "id"),
}


def _row_fields(collection: str, document: dict) -> dict[str, Any]:
    """Project a document onto its scalar columns + JSON payload."""
    payload = dict(document)
    if collection == "events":
        return {
            "id": document.get("id"),
            "timestamp": float(document.get("timestamp", 0.0)),
            "event_type": str(document.get("event_type", ""))[:64],
            "source": str(document.get("source", ""))[:64],
            "destination": str(document.get("destination", ""))[:64],
            "severity": str(document.get("severity", "INFO"))[:16],
            "message": str(document.get("message", ""))[:2000],
            "payload": payload,
        }
    if collection == "threats":
        return {
            "id": document.get("id"),
            "timestamp": float(document.get("timestamp", 0.0)),
            "threat_type": str(document.get("threat_type", ""))[:80],
            "severity": str(document.get("severity", "INFO"))[:16],
            "risk_score": int(document.get("risk_score", 0)),
            "affected_asset": str(document.get("affected_asset", ""))[:120],
            "payload": payload,
        }
    if collection == "incidents":
        return {
            "id": document.get("id"),
            "threat_type": str(document.get("threat_type", ""))[:80],
            "severity": str(document.get("severity", "INFO"))[:16],
            "status": str(document.get("status", "OPEN"))[:20],
            "risk_score": int(document.get("risk_score", 0)),
            "first_seen": float(document.get("first_seen", 0.0)),
            "last_seen": float(document.get("last_seen", 0.0)),
            "payload": payload,
        }
    if collection == "attack_paths":
        return {"incident_id": document.get("incident_id"), "payload": payload}
    if collection == "audit":
        return {
            "id": document.get("id"),
            "created_at": float(document.get("created_at", 0.0)),
            "actor_id": str(document.get("actor_id", ""))[:40],
            "actor_email": str(document.get("actor_email", ""))[:255],
            "action": str(document.get("action", ""))[:60],
            "resource": str(document.get("resource", ""))[:120],
            "detail": dict(document.get("detail") or {}),
            "ip": str(document.get("ip", ""))[:64],
            "payload": payload,
        }
    raise ValueError(f"unknown collection {collection}")


class Database:
    def __init__(self) -> None:
        self.engine = None
        self.session_factory: Optional[sessionmaker] = None
        self.mode = "disabled"
        self.url = ""
        self.error: Optional[str] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ setup
    def init(self, url: str = "", autocreate: bool = True, pool_size: int = 10) -> str:
        with self._lock:
            self.close()
            self.url = (url or "").strip()
            if not self.url:
                self.mode = "disabled"
                return self.mode
            connect_args: dict[str, Any] = {}
            kwargs: dict[str, Any] = {"pool_pre_ping": True}
            if self.url.startswith("sqlite"):
                connect_args["check_same_thread"] = False
                if ":memory:" in self.url:
                    kwargs["poolclass"] = StaticPool
            else:
                kwargs["pool_size"] = max(1, int(pool_size))
                kwargs["max_overflow"] = max(1, int(pool_size))
            try:
                self.engine = create_engine(self.url, connect_args=connect_args, **kwargs)
                self.session_factory = sessionmaker(
                    bind=self.engine, expire_on_commit=False, autoflush=False
                )
                if autocreate:
                    Base.metadata.create_all(self.engine)
                self.mode = "postgresql" if self.url.startswith(("postgres", "postgresql")) else "sqlite"
                self.error = None
                logger.info("database ready", extra={"mode": self.mode})
            except Exception as exc:  # pragma: no cover - environment dependent
                self.mode = "unavailable"
                self.error = f"{type(exc).__name__}: {exc}"
                self.engine = None
                self.session_factory = None
                logger.error("database init failed", extra={"error": self.error})
            return self.mode

    def close(self) -> None:
        if self.engine is not None:
            try:
                self.engine.dispose()
            except Exception:  # pragma: no cover
                pass
        self.engine = None
        self.session_factory = None

    @property
    def enabled(self) -> bool:
        return self.session_factory is not None

    # --------------------------------------------------------------- plumbing
    @contextmanager
    def session(self) -> Iterator[Session]:
        if self.session_factory is None:
            raise RuntimeError("database is not configured")
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> bool:
        if not self.enabled:
            return False
        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            return False

    # ------------------------------------------------------------ write path
    def write(self, collection: str, document: dict) -> None:
        """Best-effort upsert. Never raises into a request handler."""
        if not self.enabled or collection not in _COLLECTIONS:
            return
        model, _ = _COLLECTIONS[collection]
        try:
            fields = _row_fields(collection, document)
            with self.session() as session:
                session.merge(model(**fields))
        except Exception as exc:
            self.mode = "degraded"
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("write failed", extra={"collection": collection, "error": self.error})

    # -------------------------------------------------------------- read path
    def _load(self, collection: str, limit: int, desc: bool = True, order_col: str = "timestamp") -> list[dict]:
        if not self.enabled or collection not in _COLLECTIONS:
            return []
        model, _ = _COLLECTIONS[collection]
        try:
            with self.session() as session:
                stmt = session.query(model)
                if hasattr(model, order_col):
                    stmt = stmt.order_by(getattr(model, order_col).desc() if desc else getattr(model, order_col))
                rows = stmt.limit(limit).all()
            return [row.payload for row in rows]
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("load failed", extra={"collection": collection, "error": str(exc)})
            return []

    def load_events(self, limit: int = 2000) -> list[dict]:
        return list(reversed(self._load("events", limit, desc=False, order_col="timestamp")))

    def load_threats(self, limit: int = 1000) -> list[dict]:
        return self._load("threats", limit)

    def load_incidents(self, limit: int = 500) -> list[dict]:
        return self._load("incidents", limit)

    def load_graphs(self, limit: int = 500) -> list[dict]:
        return self._load("attack_paths", limit, order_col="updated_at")

    def load_audit(self, limit: int = 200) -> list[dict]:
        return self._load("audit", limit, order_col="created_at")

    def count(self, collection: str) -> int:
        if not self.enabled or collection not in _COLLECTIONS:
            return 0
        model, _ = _COLLECTIONS[collection]
        try:
            with self.session() as session:
                return int(session.query(model).count())
        except Exception:  # pragma: no cover
            return 0

    # ------------------------------------------------------------------ admin
    def clear_operational(self) -> int:
        """Delete telemetry rows only. Users, tokens and audit trail survive."""
        if not self.enabled:
            return 0
        deleted = 0
        try:
            with self.session() as session:
                for collection in ("events", "threats", "incidents", "attack_paths"):
                    model, _ = _COLLECTIONS[collection]
                    deleted += int(session.query(model).delete())
        except Exception as exc:  # pragma: no cover - environment dependent
            self.mode = "degraded"
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("clear failed", extra={"error": self.error})
        return deleted


DB = Database()
