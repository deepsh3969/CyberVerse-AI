from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
with c:
    for path in ["/api/health", "/api/dashboard", "/api/network", "/api/incidents", "/api/scenarios", "/api/settings", "/api/demo"]:
        r = c.get(path)
        print(path, r.status_code, str(r.json())[:140])
    r = c.post("/api/simulate/brute-force", json={"intensity": "normal", "replay": True})
    print("simulate", r.status_code)
    j = r.json()
    print("threats", [(t["threat_type"], t["risk_score"], t["confidence"]) for t in j["threats"]])
    inc = j["incident"]
    print("incident", inc["id"], inc["severity"], inc["risk_score"], len(inc["evidence"]))
    print("graph", [n["label"] for n in j["attack_graph"]["nodes"]])
    ra = c.post("/api/analyze", json={"incident_id": inc["id"], "question": "Why is this dangerous?"})
    print("analyze", ra.status_code, ra.json()["analysis"]["provider"], len(ra.json()["analysis"]["sections"]))
    rc = c.post(f"/api/incidents/{inc['id']}/contain")
    print("contain", rc.status_code, rc.json()["actions"][0])
    rr = c.get(f"/api/reports/{inc['id']}")
    print("report", rr.status_code, rr.json()["id"], rr.json()["status"])
    rd = c.get("/api/dashboard")
    d = rd.json()
    print("score", d["security_score"], d["threat_level"], d["active_incidents"], d["events_analyzed"], d["threat_categories"])
    # all scenarios
    for s in ["port-scan", "suspicious-login", "privilege-escalation", "data-exfiltration", "malware", "ddos", "insider-anomaly"]:
        rr = c.post(f"/api/simulate/{s}", json={"intensity": "normal"})
        jj = rr.json()
        print(s, rr.status_code, [(t["threat_type"], t["severity"], t["risk_score"]) for t in jj["threats"]],
              jj["incident"]["id"] if jj.get("incident") else None)
