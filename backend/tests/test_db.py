"""Database layer tests (SQLite; same SQLAlchemy path as PostgreSQL)."""
from __future__ import annotations

import time

import pytest

from app.db.database import DB
from app.services.store import Store

EVENT = {
    "id": "EVT-1",
    "timestamp": time.time(),
    "event_type": "NETWORK_PORT_SCAN",
    "source": "198.51.100.90",
    "destination": "firewall",
    "severity": "MEDIUM",
    "message": "Sequential SYN probes",
    "metadata": {},
}


@pytest.fixture()
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'store.db'}"
    DB.init(url, autocreate=True)
    yield url
    DB.close()
    DB.mode = "disabled"
    DB.error = None


def test_ping_and_mode(db):
    assert DB.enabled
    assert DB.ping() is True
    assert DB.mode == "sqlite"


def test_events_round_trip(db):
    DB.write("events", EVENT)
    assert DB.count("events") == 1
    loaded = DB.load_events()
    assert loaded[0]["id"] == "EVT-1"
    assert loaded[0]["message"] == "Sequential SYN probes"
    assert loaded[0]["event_type"] == "NETWORK_PORT_SCAN"


def test_threat_incident_graph_audit(db):
    DB.write("threats", {"id": "THR-1", "timestamp": time.time(), "threat_type": "Port Scan",
                         "severity": "MEDIUM", "risk_score": 57, "affected_asset": "Perimeter Firewall"})
    DB.write("incidents", {"id": "INC-1", "threat_type": "Port Scan", "severity": "MEDIUM",
                           "status": "OPEN", "risk_score": 57, "first_seen": 1.0, "last_seen": 2.0})
    DB.write("attack_paths", {"incident_id": "INC-1", "nodes": [], "edges": []})
    DB.write("audit", {"id": "AUD-1", "created_at": time.time(), "action": "auth.login",
                       "actor_email": "admin@cyberverse.local", "resource": "", "detail": {}, "ip": ""})

    assert DB.count("threats") == 1
    assert DB.count("incidents") == 1
    assert DB.count("attack_paths") == 1
    assert DB.count("audit") == 1
    assert DB.load_graphs()[0]["incident_id"] == "INC-1"
    assert DB.load_audit()[0]["action"] == "auth.login"
    assert DB.load_audit()[0]["id"] == "AUD-1"


def test_unknown_collection_is_ignored(db):
    DB.write("not-a-collection", {"id": "X"})  # must not raise
    assert DB.count("not-a-collection") == 0


def test_survives_reconnect(db):
    DB.write("events", EVENT)
    DB.close()
    assert DB.ping() is False
    DB.init(db, autocreate=True)
    assert DB.count("events") == 1


def test_hydrate_restores_store(db):
    DB.write("events", EVENT)
    DB.write("threats", {"id": "THR-1", "timestamp": 100.0, "threat_type": "Port Scan",
                         "severity": "HIGH", "risk_score": 80, "affected_asset": "Perimeter Firewall",
                         "confidence": 0.9, "anomaly_score": 0.5,
                         "source": "1.2.3.4", "destination": "firewall",
                         "evidence": ["x"], "detector": "rules", "status": "ACTIVE"})
    DB.write("incidents", {"id": "INC-1", "threat_type": "Port Scan", "severity": "HIGH",
                           "risk_score": 80, "status": "OPEN", "first_seen": 1.0, "last_seen": 2.0,
                           "affected_assets": ["Perimeter Firewall"], "source": "1.2.3.4",
                           "destination": "firewall", "evidence": [], "timeline": [],
                           "threat_ids": ["THR-1"], "recommendations": [], "analysis": None,
                           "containment": None})

    store = Store()
    counts = store.hydrate()
    assert counts["events"] == 1
    assert counts["threats"] == 1
    assert counts["incidents"] == 1
    assert store.seeded is True
    assert store.events_analyzed == 1
    assert "INC-1" in store.incidents
    assert "THR-1" in store.threats
    # node risk rebuilt from the restored threat
    assert store.node_status.get("firewall") in ("warning", "compromised")

    # hydrating again must not duplicate events
    store2 = Store()
    store2.hydrate()
    assert len(store2.events) == 1


def test_full_reset_clears_telemetry_keeps_audit(db):
    DB.write("events", EVENT)
    DB.write("audit", {"id": "AUD-1", "created_at": time.time(), "action": "auth.login",
                       "actor_email": "a@b.co", "resource": "", "detail": {}, "ip": ""})
    store = Store()
    store.full_reset()
    assert DB.count("events") == 0
    assert DB.count("audit") == 1
    assert store.seeded is False


def test_disabled_database_is_a_no_op():
    assert not DB.enabled
    DB.write("events", EVENT)  # must not raise
    assert DB.load_events() == []
    assert DB.ping() is False
    assert DB.clear_operational() == 0
