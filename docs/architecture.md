# Architecture

## Overview

CyberVerse AI is a two-tier application: a React SPA (command center) and a FastAPI service (detection
core). The backend owns all state; the frontend polls it and degrades to bundled preview data when it
cannot be reached.

```
Browser (React SPA)
   │  fetch /api/* (timeout + fallback, 401 → silent refresh → retry)
   ▼
FastAPI
   │  RequestContextMiddleware (request-id, security headers, access log, metrics)
   │  RBAC deps: viewer / analyst / admin  (JWT bearer + rotating refresh cookie)
   ▼
Engine (simulate → features → detect → incident → graph → contain)
   │
   ├── ThreatDetector (Isolation Forest + rule engine)
   ├── Analyst (local engine | optional LLM)
   ├── Store (thread-safe in-memory ⇄ PostgreSQL mirror)
   │      └── SQLAlchemy 2 · Alembic · users / refresh tokens / audit logs
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
per-node status/risk and score history. `Persistence` mirrors writes to PostgreSQL when `DATABASE_URL` is
configured (SQLAlchemy 2, models in `db/models.py`) and swallows connection errors so demo mode always
works. On startup `bootstrap.py` hydrates the store from the database, so restarts keep incidents,
graphs, users and audit history. Schema changes are versioned with Alembic (`backend/alembic/`).

### `core/security.py` + `api/auth.py` + `api/deps.py`
Authentication and authorization:

- `security.py` — bcrypt password hashing, HS256 JWT mint/verify, SHA-256 refresh-token hashing.
- `auth.py` — `POST /login` (per-IP rate limit), `POST /refresh` (rotates the HttpOnly `cv_rt` cookie),
  `POST /logout`, `GET /me`, `POST /password`, user CRUD, `GET /audit`.
- `deps.py` — FastAPI dependencies `require_user`, `require_read`, `require_role("analyst"|"admin")`;
  when auth is inactive the anonymous demo user passes every check.
- `services/users.py` — `UserRepository` with PostgreSQL backend and in-memory fallback;
  role order `viewer < analyst < admin`.

Auth is enforced only when `AUTH_ENABLED=true` **and** `DATABASE_URL` is set; production startup
(`core/config.py::validate()`) fails fast on missing `JWT_SECRET`, `DATABASE_URL`, admin password or
explicit `CORS_ORIGINS`.

### `core/middleware.py` + `api/ratelimit.py` + `services/audit.py`
Cross-cutting request pipeline: request IDs (`X-Request-ID`), JSON/text structured logs
(`core/logging.py`), security headers (+ HSTS in production), 413 body cap, per-IP sliding-window
rate limiting with a separate stricter budget for logins, and audit records (actor, action, resource,
IP, payload) persisted to `audit_logs` and queryable via `GET /api/audit`.

### `api/observability.py` + `core/metrics.py`
`GET /api/health` (liveness), `GET /api/ready` (readiness — pings the database), `GET /metrics`
(Prometheus text: request counters, latency histograms, login/simulation counters, database gauge).
Metrics stay on the API tier; the bundled nginx returns 404 for `/metrics`.

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

- JWT auth with rotating opaque refresh tokens (hashed at rest), bcrypt passwords, three roles, audit
  trail; per-IP login throttling; all writes require `analyst+`, destructive reset requires `admin`.
- CORS restricted to configured origins; all inputs validated by Pydantic; 1 MiB body cap.
- Rate limiting per client IP on the general and login paths.
- Secrets only in backend env vars; production fails fast on missing/weak config; `/api/settings`
  exposes non-sensitive configuration only.
- Frontend timeouts on every request, silent 401-refresh-retry, offline banner, bundled preview
  dataset, per-page empty/error states; role-aware controls (read-only UI for `viewer`).
- No offensive capability: events are records in memory, nothing is sent anywhere.
