# API Reference

Base URL: `http://localhost:8000` · prefix `/api` · interactive docs at `/docs`.
All bodies are JSON. Errors return `{ "detail": string }`.

## Meta

### `GET /`
Service descriptor (`{"name": ..., "docs": "/docs", ...}`) when no frontend build is present; otherwise it
serves the SPA landing page (`index.html`).

### `GET /api/health`
```json
{ "status": "ok", "version": "1.0.0", "database": "disabled",
  "ai_provider": "local-analysis-engine", "ml_backend": "isolation-forest",
  "uptime_seconds": 42.0 }
```

### `GET /api/settings`
Non-secret runtime configuration (app name, database mode, provider, rate limit, asset count).

### `GET /api/scenarios`
```json
{ "items": [ { "key": "brute-force", "name": "Brute Force Simulation",
               "severity": "HIGH", "description": "…" } ] }
```

## Data

### `GET /api/dashboard`
Security score, threat level, counters and five chart series:
`events_over_time`, `threat_categories`, `risk_history`, `event_volume`,
`severity_distribution`, `recent_threats`, `top_assets`.

### `GET /api/network`
```json
{ "nodes": [ { "id": "auth", "label": "Authentication Server", "type": "server",
               "status": "warning", "risk": 48, "ip": "10.20.1.30",
               "zone": "internal", "position": [0, -3.4, 3.6] } ],
  "edges": [ { "source": "web", "target": "api", "label": "rest", "status": "idle" } ] }
```
`status` ∈ `healthy | warning | compromised | monitoring | contained`;
edge `status` ∈ `idle | warning | attack | contained`.

### `GET /api/events?limit=120&offset=0&event_type=`
```json
{ "items": [ { "id": "EVT-…", "event_type": "AUTH_LOGIN_FAILED", "source": "203.0.113.44",
               "destination": "auth", "severity": "MEDIUM", "message": "…",
               "timestamp": 1767225600.123, "metadata": { } } ],
  "total": 312, "analyzed": 312 }
```

### `GET /api/events/stream`
Server-sent events (`text/event-stream`), one payload per second while events change.

### `GET /api/threats?limit=50`
```json
{ "items": [ { "id": "THR-…", "threat_type": "Brute Force", "severity": "HIGH",
               "risk_score": 96, "confidence": 0.978, "anomaly_score": 0.81,
               "affected_asset": "Authentication Server", "source": "203.0.113.44",
               "evidence": [ "7 failed login attempts …" ],
               "detector": "isolation-forest + rules", "status": "ACTIVE" } ],
  "total": 3 }
```

## Incidents

### `GET /api/incidents?status=OPEN`
### `GET /api/incidents/{id}`
```json
{ "incident": { "id": "INC-…", "threat_type": "Brute Force", "severity": "HIGH",
                "risk_score": 96, "status": "OPEN", "first_seen": 1767225600,
                "last_seen": 1767225612, "affected_assets": ["Authentication Server"],
                "evidence": [], "timeline": [], "recommendations": [], "analysis": null,
                "containment": null },
  "attack_graph": { "nodes": [], "edges": [], "path_labels": [] } }
```

### `PATCH /api/incidents/{id}/status`
Body: `{ "status": "INVESTIGATING" }` ∈ `OPEN | INVESTIGATING | CONTAINED | RESOLVED`.

### `POST /api/incidents/{id}/contain`
```json
{ "message": "THREAT CONTAINED",
  "actions": ["Endpoint isolated (simulated)", "Suspicious session terminated (simulated)",
              "Threat path blocked at the firewall (simulated)",
              "Monitoring increased on related assets (simulated)"],
  "incident": { "status": "CONTAINED", "containment": { "mode": "simulation" } } }
```

## Attack graph

### `GET /api/attack-graph` · `GET /api/attack-graph/{incident_id}`
```json
{ "incident_id": "INC-…",
  "nodes": [ { "id": "attacker", "label": "External Attacker", "kind": "attacker",
               "status": "monitoring", "risk": 70 },
             { "id": "auth", "label": "Authentication Server", "kind": "asset",
               "status": "compromised", "risk": 68, "compromised_at": 1767225612 } ],
  "edges": [ { "source": "attacker", "target": "internet", "active": true,
               "severity": "HIGH" } ],
  "path_labels": ["External Attacker", "Internet", "…"] }
```

## Simulation

### `POST /api/simulate/{scenario}`
`scenario` ∈ `port-scan | brute-force | suspicious-login | privilege-escalation |
data-exfiltration | malware | ddos | insider-anomaly`

Body: `{ "intensity": "low|normal|high", "target": "" }` (all optional).

```json
{ "scenario": "Brute Force Simulation",
  "events": [ … ], "threats": [ … ],
  "incident": { "id": "INC-…", … },
  "attack_graph": { … },
  "message": "Credential attack against the identity provider …" }
```

## Analysis & reports

### `POST /api/analyze`
Body: `{ "incident_id": "INC-…", "question": "Why is this dangerous?" }`

```json
{ "analysis": { "provider": "local-analysis-engine", "summary": "…",
                "sections": [ { "heading": "What happened?", "body": "…" } ],
                "recommendations": [ { "title": "…", "detail": "…", "priority": "HIGH" } ],
                "generated_at": 1767225613 },
  "incident": { … } }
```

### `GET /api/reports/{incident_id}`
Full printable report: executive summary, threat detail, evidence, AI analysis, recommended response,
containment status, attack path, timeline.

## Demo

| Endpoint | Effect |
| --- | --- |
| `GET /api/demo` | Current step, label, detail, state, `incident_id`, 12-step index |
| `POST /api/demo/start` | Starts the scripted walkthrough (idempotent while running) |
| `POST /api/demo/reset` | Restores baseline telemetry and resets the sequence |
| `POST /api/demo/stop` | Aborts the running sequence |

States: `idle | running | timeout (awaiting containment) | complete | failed | aborted`.

## Sandbox

### `POST /api/reset`
Clears events, threats, incidents, graphs and node states, then reseeds baseline data.

## Errors

| Status | Meaning |
| --- | --- |
| 404 | Unknown incident / scenario / graph / report |
| 422 | Schema validation failure (e.g. invalid `intensity` or `status`) |
| 429 | Rate limit exceeded (`RATE_LIMIT_PER_MINUTE`) |
| 500 | Unexpected error — returns `{ "detail": "ExceptionType: message" }` |
