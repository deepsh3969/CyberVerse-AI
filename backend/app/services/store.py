"""In-memory application state with optional PostgreSQL persistence.

The in-memory store is the source of truth so the product always works
("DEMO MODE") even with no database configured. When `DATABASE_URL` is set
every mutation is written through to PostgreSQL and the store is hydrated
from it at startup, so state survives restarts.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from typing import Any, Optional

from app.core.config import settings
from app.db.database import DB
from app.models.schemas import (
    Incident,
    IncidentStatus,
    Severity,
    Threat,
)
from app.services import topology

logger = logging.getLogger("cyberverse.store")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class Persistence:
    """Write-through mirror to the configured database (best-effort, never raises)."""

    @property
    def mode(self) -> str:
        return DB.mode

    def write(self, collection: str, document: dict) -> None:
        DB.write(collection, document)


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.started_at = time.time()
        self.persistence = Persistence()
        self.events: deque[dict] = deque(maxlen=settings.max_events_retained)
        self.threats: dict[str, Threat] = {}
        self.incidents: dict[str, Incident] = {}
        self.graphs: dict[str, dict] = {}
        self.reports: dict[str, dict] = {}
        self.node_status: dict[str, str] = {n["id"]: "healthy" for n in topology.NODES}
        self.node_risk: dict[str, int] = {
            n["id"]: 8 + (topology.ASSET_SENSITIVITY[n["id"]] // 12)
            for n in topology.NODES
        }
        self.events_analyzed = 0
        self.threats_blocked = 0
        self.risk_history: list[dict] = []
        self.seeded = False
        self.demo: dict[str, Any] = {"state": "idle", "step": -1, "started_at": None}

    # ------------------------------------------------------------------ events
    def add_event(self, event: dict) -> dict:
        with self.lock:
            self.events.append(event)
            self.events_analyzed += 1
            self.persistence.write("events", event)
            return event

    def list_events(self, limit: int = 200, offset: int = 0, event_type: str = "") -> list[dict]:
        with self.lock:
            items = list(self.events)
        if event_type:
            items = [e for e in items if e["event_type"] == event_type]
        items = items[::-1]
        return items[offset : offset + limit]

    # ----------------------------------------------------------------- threats
    def add_threat(self, threat: Threat) -> Threat:
        with self.lock:
            self.threats[threat.id] = threat
            self.persistence.write("threats", threat.model_dump(mode="json"))
            self._bump_node(threat.affected_asset, threat.severity)
            return threat

    def list_threats(self, limit: int = 100) -> list[Threat]:
        with self.lock:
            return sorted(self.threats.values(), key=lambda t: t.timestamp, reverse=True)[:limit]

    # -------------------------------------------------------------- incidents
    def add_incident(self, incident: Incident) -> Incident:
        with self.lock:
            self.incidents[incident.id] = incident
            self.persistence.write("incidents", incident.model_dump(mode="json"))
            return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        with self.lock:
            return self.incidents.get(incident_id)

    def list_incidents(self) -> list[Incident]:
        with self.lock:
            return sorted(self.incidents.values(), key=lambda i: i.first_seen, reverse=True)

    def set_incident_status(self, incident_id: str, status: IncidentStatus) -> Optional[Incident]:
        with self.lock:
            inc = self.incidents.get(incident_id)
            if not inc:
                return None
            inc.status = status
            inc.timeline.append(
                {
                    "time": time.time(),
                    "kind": "status",
                    "label": f"Status changed to {status.value}",
                    "detail": "Manual analyst update (simulated console action).",
                }
            )
            self.persistence.write("incidents", inc.model_dump(mode="json"))
            return inc

    # ------------------------------------------------------------ attack graph
    def set_graph(self, incident_id: str, graph: dict) -> dict:
        with self.lock:
            self.graphs[incident_id] = graph
            self.persistence.write("attack_paths", graph)
            return graph

    def get_graph(self, incident_id: str) -> Optional[dict]:
        with self.lock:
            return self.graphs.get(incident_id)

    def list_graphs(self) -> list[dict]:
        with self.lock:
            return list(self.graphs.values())

    # ------------------------------------------------------------------ nodes
    def _bump_node(self, label_or_id: str, severity: Severity) -> None:
        node_id = label_or_id
        for n in topology.NODES:
            if n["label"] == label_or_id or n["id"] == label_or_id:
                node_id = n["id"]
                break
        if node_id not in self.node_status:
            return
        weight = {
            Severity.INFO: 2,
            Severity.LOW: 5,
            Severity.MEDIUM: 12,
            Severity.HIGH: 22,
            Severity.CRITICAL: 32,
        }[severity]
        self.node_risk[node_id] = min(100, self.node_risk[node_id] + weight)
        current = self.node_status[node_id]
        if weight >= 22:
            self.node_status[node_id] = "compromised"
        elif weight >= 12 and current == "healthy":
            self.node_status[node_id] = "warning"
        elif current == "healthy" and weight >= 5:
            self.node_status[node_id] = "monitoring"

    def set_node_status(self, node_id: str, status: str, risk: Optional[int] = None) -> None:
        with self.lock:
            if node_id in self.node_status:
                self.node_status[node_id] = status
            if risk is not None and node_id in self.node_risk:
                self.node_risk[node_id] = max(0, min(100, risk))

    def reset_nodes(self) -> None:
        with self.lock:
            for n in topology.NODES:
                self.node_status[n["id"]] = "healthy"
                self.node_risk[n["id"]] = 8 + (topology.ASSET_SENSITIVITY[n["id"]] // 12)

    # ------------------------------------------------------------------ scores
    def security_score(self) -> int:
        with self.lock:
            active = [
                i for i in self.incidents.values() if i.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)
            ]
            penalty = sum(max(0, i.risk_score - 55) for i in active) // 3
            node_penalty = sum(
                max(0, r - 30) // 3
                for node_id, r in self.node_risk.items()
                if self.node_status.get(node_id) in ("warning", "compromised")
            )
            base = 96 - penalty - node_penalty
            return max(12, min(99, int(base)))

    def record_risk(self) -> dict:
        score = self.security_score()
        point = {"time": time.time(), "score": score}
        with self.lock:
            self.risk_history.append(point)
            if len(self.risk_history) > 180:
                self.risk_history = self.risk_history[-180:]
        return point

    # ------------------------------------------------------------------ resets
    def full_reset(self) -> None:
        with self.lock:
            self.events.clear()
            self.threats.clear()
            self.incidents.clear()
            self.graphs.clear()
            self.reports.clear()
            self.events_analyzed = 0
            self.threats_blocked = 0
            self.risk_history.clear()
            self.demo = {"state": "idle", "step": -1, "started_at": None}
            self.reset_nodes()
            self.seeded = False
        DB.clear_operational()

    # ------------------------------------------------------------- hydration
    def hydrate(self, events_limit: Optional[int] = None) -> dict[str, int]:
        """Load persisted telemetry into memory (no-op without a database).

        Returns the number of rows restored per collection. Node status is
        rebuilt deterministically from the restored threats so a restart does
        not accumulate risk across process lifetimes.
        """
        if not DB.enabled:
            return {"events": 0, "threats": 0, "incidents": 0, "graphs": 0}
        limit = events_limit or settings.db_events_loaded
        events = DB.load_events(limit)
        threats = DB.load_threats()
        incidents = DB.load_incidents()
        graphs = DB.load_graphs()
        counts = {
            "events": len(events),
            "threats": len(threats),
            "incidents": len(incidents),
            "graphs": len(graphs),
        }
        if not any(counts.values()):
            return counts

        restored_threats: list[Threat] = []
        with self.lock:
            seen = {e.get("id") for e in self.events}
            for ev in events:
                if ev.get("id") and ev["id"] not in seen:
                    self.events.append(ev)
                    seen.add(ev["id"])
            self.events_analyzed += counts["events"]

            for payload in threats:
                try:
                    threat = Threat(**payload)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("skipped threat on hydrate: %s", exc)
                    continue
                self.threats[threat.id] = threat
                restored_threats.append(threat)

            for payload in incidents:
                try:
                    incident = Incident(**payload)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("skipped incident on hydrate: %s", exc)
                    continue
                self.incidents[incident.id] = incident

            for graph in graphs:
                if graph.get("incident_id"):
                    self.graphs[graph["incident_id"]] = graph

            # Rebuild node state from the restored threats.
            self.reset_nodes()
            for threat in sorted(restored_threats, key=lambda t: t.timestamp):
                self._bump_node(threat.affected_asset, threat.severity)
            self.threats_blocked = sum(1 for t in restored_threats if t.status == "CONTAINED")
            self.seeded = True
        logger.info("store hydrated", extra=counts)
        return counts


STORE = Store()
