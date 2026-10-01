# Architecture

## Overview

CyberVerse AI is a two-tier application: a React SPA (command center) and a FastAPI service (detection
core). The backend owns all state; the frontend polls it and degrades to bundled preview data when it
cannot be reached.

```
Browser (React SPA)
   │  fetch /api/* (timeout + fallback)
   ▼
FastAPI  ──► Engine (simulate → features → detect → incident → graph → contain)
   │              │
   │              ├── ThreatDetector (Isolation Forest + rule engine)
   │              ├── Analyst (local engine | optional LLM)
   │              └── Store (thread-safe in-memory ⇄ MongoDB mirror)
   ▼
Response JSON  ◄── Dashboard aggregation, timelines, reports
```

## Backend components

### `services/topology.py`
Static description of the sandbox: 10 nodes (Internet, User Devices, Remote Access Gateway, Firewall,
Web Server, API Server, Authentication Server, Database, SOC, AI Engine), 14 links, asset sensitivity
values and human labels. This is the single source of truth for both the API and the attack graphs.

### `services/store.py`
Thread-safe in-memory store (`RLock`) holding events (bounded deque), threats, incidents, attack graphs,
per-node status/risk and score history. `Persistence` mirrors writes to MongoDB when `MONGODB_URI` is
configured and swallows connection errors so demo mode always works.

### `simulator/scenarios.py`
Eight scenario builders emit timestamped event sequences with metadata (`evidence`, `guaranteed`,
`port`, `bytes_out`, …). Sources use RFC 5737 documentation addresses. `normal_event()` / `seed_events()`
produce the benign baseline used at startup.

### `ml/features.py` + `ml/detector.py`
`FeatureBuilder` maintains rolling windows per event type/source/destination and emits a 13-D vector per
event. `ThreatDetector` trains an Isolation Forest on a procedurally generated benign baseline, scores
events, runs the rule engine (brute force, port scan, and per-event rules) and builds `Threat` objects
with evidence and confidence.

### `services/engine.py`
Orchestration layer:

1. `run_scenario()` — ingest events → detect → create/merge incident → build attack graph → record risk.
2. `contain()` — mark incident contained, downgrade node states, deactivate graph edges, bump
   `threats_blocked`, append timeline entry.
3. `dashboard()` — bucketed event/threat series, category counts, severity distribution, top assets,
   security score and threat level.
4. `seed()` — benign event baseline, one resolved case and one investigating case so every console has
   content on first load; retrains the detector on observed benign traffic.

### `services/analyst.py`
Local explanation engine (deterministic, always available) plus an optional OpenAI-compatible chat call.
Any LLM failure falls back silently.

### `services/demo.py`
`DemoRunner` executes a 12-step narrative in a background thread, updating a pollable state document.
Step 10 waits (90 s) for the analyst to press **Contain Threat**, then finishes with recovery.

### `api/routes.py`
Thin handlers over the engine, each protected by a sliding-window per-IP rate limiter, plus an SSE
stream endpoint.

## Frontend components

| Layer | Responsibility |
| --- | --- |
| `AppContext` | health check + polling loop, data cache, action wrappers, toasts, preferences |
| `services/api.js` | fetch wrapper with timeout, typed `ApiError`, `withFallback` |
| `CommandCenterLayout` | sidebar navigation, topbar (connection pill, demo control), offline banner |
| `pages/*` | feature screens; each renders from context data only |
| `three/NetworkScene` | R3F canvas: nodes, links, packets, selection, camera reset |
| `charts/*` | Recharts wrappers with a shared dark theme |

### Data flow for a simulation

1. **Simulator page** → `POST /api/simulate/{scenario}`.
2. Backend ingests events, runs detection, creates threat + incident + graph.
3. Context refresh (`GET /dashboard`, `/network`, `/incidents`, `/threats`, `/events`) picks up the result.
4. Overview KPIs and charts re-render; 3D nodes recolour; the storyline ribbon advances.
5. Incident detail → `POST /api/analyze` → sections + recommendations.
6. **Contain Threat** → `POST /api/incidents/{id}/contain` → banner, node states, timeline, scores update.

## Security & resilience

- CORS restricted to configured origins; all inputs validated by Pydantic.
- Rate limiting per client IP; request bodies capped by schema constraints.
- Secrets only in backend env vars; `/api/settings` exposes non-sensitive configuration.
- Frontend timeouts on every request, offline banner, bundled preview dataset, per-page empty/error states.
- No offensive capability: events are records in memory, nothing is sent anywhere.
