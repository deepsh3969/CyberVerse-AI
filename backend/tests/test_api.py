import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ml_backend"] == "isolation-forest"
    assert body["database"] in ("disabled", "sqlite", "postgresql") or body["database"].startswith("unavailable")


def test_dashboard_shape(client):
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "security_score",
        "threat_level",
        "active_incidents",
        "protected_assets",
        "events_analyzed",
        "events_over_time",
        "threat_categories",
        "risk_history",
        "severity_distribution",
    ):
        assert key in body
    assert 0 <= body["security_score"] <= 100
    assert body["events_analyzed"] > 0


def test_network_topology(client):
    r = client.get("/api/network")
    assert r.status_code == 200
    body = r.json()
    assert len(body["nodes"]) >= 9
    assert len(body["edges"]) >= 10
    ids = {n["id"] for n in body["nodes"]}
    assert {"internet", "firewall", "auth", "db", "ai"} <= ids


def test_scenarios_listed(client):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    keys = {i["key"] for i in r.json()["items"]}
    assert keys == {
        "port-scan",
        "brute-force",
        "suspicious-login",
        "privilege-escalation",
        "data-exfiltration",
        "malware",
        "ddos",
        "insider-anomaly",
    }


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("port-scan", "Port Scan"),
        ("brute-force", "Brute Force"),
        ("data-exfiltration", "Data Exfiltration"),
        ("malware", "Malware Activity"),
        ("ddos", "DDoS Traffic Spike"),
        ("insider-anomaly", "Insider Threat"),
    ],
)
def test_simulation_detects_threat(client, scenario, expected):
    r = client.post(f"/api/simulate/{scenario}", json={"intensity": "normal", "replay": True})
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) > 0
    assert body["threats"], "detection engine must return at least one threat"
    threat = body["threats"][0]
    assert threat["threat_type"] == expected
    assert 0 <= threat["risk_score"] <= 100
    assert 0 < threat["confidence"] <= 1
    assert threat["evidence"]
    assert body["incident"] is not None
    assert body["incident"]["id"].startswith("INC-")
    assert body["attack_graph"] is not None
    assert len(body["attack_graph"]["nodes"]) >= 3


def test_unknown_scenario(client):
    r = client.post("/api/simulate/not-a-scenario", json={})
    assert r.status_code == 404


def test_validation_error(client):
    r = client.post("/api/simulate/brute-force", json={"intensity": "not-valid"})
    assert r.status_code == 422


def test_incident_flow_and_containment(client):
    r = client.post("/api/simulate/privilege-escalation", json={"intensity": "normal"})
    inc_id = r.json()["incident"]["id"]

    detail = client.get(f"/api/incidents/{inc_id}").json()
    assert detail["incident"]["id"] == inc_id
    assert detail["attack_graph"] is not None

    patch = client.patch(f"/api/incidents/{inc_id}/status", json={"status": "INVESTIGATING"})
    assert patch.status_code == 200
    assert patch.json()["incident"]["status"] == "INVESTIGATING"

    bad = client.patch(f"/api/incidents/{inc_id}/status", json={"status": "NONSENSE"})
    assert bad.status_code == 422

    contain = client.post(f"/api/incidents/{inc_id}/contain")
    assert contain.status_code == 200
    body = contain.json()
    assert body["message"] == "THREAT CONTAINED"
    assert body["incident"]["status"] == "CONTAINED"
    assert len(body["actions"]) == 4
    assert "(simulated)" in body["actions"][0]

    network = client.get("/api/network").json()
    statuses = {n["id"]: n["status"] for n in network["nodes"]}
    assert statuses["api"] == "contained"


def test_missing_incident_404(client):
    assert client.get("/api/incidents/INC-DOESNOTEXIST").status_code == 404
    assert client.post("/api/incidents/INC-DOESNOTEXIST/contain").status_code == 404
    assert client.post("/api/analyze", json={"incident_id": "INC-NOPE"}).status_code == 404


def test_ai_analysis_fallback(client):
    r = client.post("/api/simulate/brute-force", json={"intensity": "normal"})
    inc_id = r.json()["incident"]["id"]
    res = client.post("/api/analyze", json={"incident_id": inc_id, "question": "What should we do?"})
    assert res.status_code == 200
    analysis = res.json()["analysis"]
    assert analysis["provider"] == "local-analysis-engine"
    assert analysis["summary"]
    headings = [s["heading"] for s in analysis["sections"]]
    assert "Analyst answer" in headings
    assert any("Evidence" == h for h in headings)
    assert analysis["recommendations"]


def test_report_generation(client):
    r = client.post("/api/simulate/ddos", json={"intensity": "low"})
    inc_id = r.json()["incident"]["id"]
    rep = client.get(f"/api/reports/{inc_id}")
    assert rep.status_code == 200
    body = rep.json()
    assert body["executive_summary"]
    assert body["ai_analysis"]["sections"]
    assert body["timeline"]
    assert body["threat_type"] == "DDoS Traffic Spike"


def test_events_endpoint(client):
    r = client.get("/api/events?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 5
    assert body["analyzed"] > 0


def test_settings_has_no_secrets(client):
    body = client.get("/api/settings").json()
    blob = str(body).lower()
    assert "api_key" not in blob
    assert "mongodb_uri" not in blob
    assert "database_url" not in blob
    assert "jwt" not in blob
    assert body["auth_enabled"] is False


def test_attack_graph_endpoint(client):
    graphs = client.get("/api/attack-graph").json()
    assert graphs["total"] >= 1
    gid = graphs["items"][0]["incident_id"]
    g = client.get(f"/api/attack-graph/{gid}")
    assert g.status_code == 200
    assert g.json()["edges"]


def test_demo_status(client):
    body = client.get("/api/demo").json()
    assert body["state"] in ("idle", "running", "complete", "timeout", "failed", "aborted", "busy")
    assert len(body["steps"]) == 12
