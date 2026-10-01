# CYBERVERSE AI

**AI-Powered 3D Cybersecurity Command Center**

> SEE THE ATTACK. UNDERSTAND THE THREAT. STOP IT.

CyberVerse AI simulates a company's digital infrastructure, generates safe synthetic cyber events, detects
and classifies threats with a local ML engine, explains them with an AI analyst, reconstructs the attack
path in 3D, and lets an analyst contain the threat — all inside a defensive sandbox.

![status](https://img.shields.io/badge/status-working%20prototype-blue) ![frontend](https://img.shields.io/badge/frontend-React%20%2B%20Three.js-38d6f5) ![backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20scikit--learn-ff3b5c)

**Live demo:** https://cyberverse-ai.vercel.app · **Source:** https://github.com/deepsh3969/CyberVerse-AI

---

## Problem statement

Security teams drown in raw telemetry. Alerts arrive without context, attack paths live in head diagrams,
and "what happened / why should I care / what do I do" is answered differently by every tool. Junior
analysts struggle to connect a failed-login burst to lateral movement, and defenders have no safe way to
rehearse an attack-to-containment workflow.

## Solution

CyberVerse AI turns that workflow into a **visible, interactive product**:

```
NORMAL → ANOMALY → THREAT → AI INVESTIGATION → ATTACK PATH → AI RESPONSE → CONTAINMENT → RECOVERY
```

A 3D network shows the infrastructure. A safe simulator produces synthetic attacks. A hybrid ML + rule
engine classifies them with evidence and risk scores. An AI analyst explains each incident. An attack graph
reconstructs the lateral path. One click runs a simulated containment playbook and the network returns to a
secure state.

---

## Key features

| Area | What works |
| --- | --- |
| **Overview dashboard** | Security score, threat level, active incidents, events analyzed, threats blocked, protected assets + 5 live Recharts visualizations that update as events arrive |
| **3D cyber network** | React Three Fiber scene with 10 assets, animated links, travelling data packets, orbit/zoom, node click inspector, red active-attack edges, camera reset |
| **Attack simulator** | 8 synthetic scenarios (port scan, brute force, suspicious login, privilege escalation, data exfiltration, malware-like activity, DDoS spike, insider anomaly) with low/normal/high intensity |
| **Detection engine** | Feature extraction per event → **Isolation Forest** anomaly score + explainable rule engine → threat type, severity, risk 0–100, confidence, evidence list |
| **AI Analyst** | 7 preset questions + free text; structured sections (what/why/evidence/systems/timeline/prevention). Uses an external LLM only when `AI_API_KEY` is set, otherwise a local analysis engine that never fails |
| **Attack graph** | Reconstructed path Attacker → Internet → … → Database, per-hop status/risk/timestamps, clickable node details with AI assessment |
| **Incident management** | Case record with evidence, timeline, status workflow (OPEN → INVESTIGATING → CONTAINED → RESOLVED), recommendations, containment log |
| **Containment simulation** | `CONTAIN THREAT` marks the case contained, isolates nodes, deactivates attack edges, updates scores and appends a timeline entry |
| **Live event stream** | Filterable, pausable console with timestamps and severity coloring |
| **Reports** | Full incident report with executive summary, evidence, timeline, AI analysis, response plan → print to PDF or export standalone HTML |
| **Hackathon demo** | One button runs a repeatable ~2 minute scripted narrative with a 12-step progress indicator |
| **Auth, roles, audit** | JWT access tokens + rotating HttpOnly refresh cookie; roles `viewer / analyst / admin`; bcrypt passwords; per-IP login limits; audit trail of logins, containment, resets, user changes (`GET /api/audit`) |
| **Production runtime** | PostgreSQL persistence (SQLAlchemy 2 + Alembic), Docker Compose (db + API + nginx), Prometheus `/metrics`, `/api/ready` readiness, structured JSON logs with request IDs, fail-fast config validation |
| **Resilience** | Backend offline → bundled preview data + clear banner; invalid responses, timeouts and missing config all degrade gracefully |

## Architecture

```
┌──────────────────────────────┐        ┌─────────────────────────────────────┐
│  frontend/  (React + Vite)   │  HTTP  │  backend/  (FastAPI)                │
│  ─ Landing / Command Center  │◄──────►│  ─ REST API  /api/*                 │
│  ─ 3D network (R3F/Three)    │  JSON  │  ─ JWT auth + RBAC + audit          │
│  ─ Charts (Recharts)         │        │  ─ Simulator (8 synthetic scripts)  │
│  ─ State + polling + fallback│        │  ─ Feature extraction               │
│  ─ Login / role-aware UI     │        │  ─ Isolation Forest + rule engine   │
└──────────────────────────────┘        │  ─ Incident / graph / containment   │
                                        │  ─ AI analyst (local or LLM)        │
                                        │  ─ In-memory store ⇄ PostgreSQL     │
                                        └──────────────────┬──────────────────┘
                                                           │ Docker Compose
                                                ┌──────────▼──────────┐
                                                │  PostgreSQL 16      │
                                                │  (SQLAlchemy +      │
                                                │   Alembic)          │
                                                └─────────────────────┘
```

Detailed documents: [`docs/architecture.md`](docs/architecture.md) ·
[`docs/api.md`](docs/api.md) · [`docs/deployment.md`](docs/deployment.md) ·
[`docs/production.md`](docs/production.md) · [`docs/demo-script.md`](docs/demo-script.md)

## AI / ML architecture

1. **Feature extraction** (`backend/app/ml/features.py`) — for every event: event frequency, failed-login
   count, inter-arrival interval, source/destination frequency, request count, bytes out, port spread,
   cyclic hour-of-day encoding, asset sensitivity, severity code, rare-event flag (13 dimensions).
2. **Anomaly model** — scikit-learn **Isolation Forest** (140 trees, contamination 0.045) trained at startup
   on a procedurally generated benign baseline (no model download). Persistable via `python ml/train.py`.
3. **Rule engine** (`backend/app/ml/detector.py`) — deterministic, explainable detections for brute force,
   port scan, privilege escalation, exfiltration, malware, DDoS, insider threat, suspicious login.
4. **Fusion** — rules decide *what* the threat is; the model modulates confidence and risk and contributes
   evidence lines. If the model were unavailable the rules still produce a working demo.
5. **AI analyst** (`backend/app/services/analyst.py`) — builds a structured explanation from incident
   metadata; optionally delegates to an OpenAI-compatible chat endpoint and falls back on any error.

## 3D visualization

- Low-poly geometry per asset type (sphere/box/cylinder/octahedron/torus/icosahedron), ~10 nodes and 14
  links — light enough for a normal laptop.
- Node colour encodes state: **green** healthy · **yellow** warning · **red** compromised ·
  **blue** monitoring/contained.
- Links animate continuously; packets travel the edges and turn red along active attack paths.
- `OrbitControls` with damping, zoom limits, node click inspector and camera reset.
- Animation density is user-configurable (Settings → animation intensity, including 0 = still).

## Cybersecurity methodology

- **Defensive only.** Every event is fabricated in-process. No packet leaves the machine, no real host is
  scanned, probed, exploited or contacted. External IPs use RFC 5737 documentation ranges
  (`198.51.100.0/24`, `203.0.113.0/24`).
- Detection follows the standard SOC pipeline: collect → enrich/features → detect → classify → score →
  investigate → respond → contain → report.
- Risk scoring blends base severity, anomaly strength, asset sensitivity and event volume.
- Containment and response actions are labelled *simulated* everywhere in the UI.

## Technology stack

**Frontend:** React 18 · Vite · Tailwind CSS · Three.js + React Three Fiber + drei · Recharts ·
Lucide React · Framer Motion · React Router · Vitest + Testing Library

**Backend:** Python 3.11 · FastAPI · Pydantic · scikit-learn · NumPy · pandas · Uvicorn · pytest

**Database & auth:** PostgreSQL 16 · SQLAlchemy 2 · Alembic · PyJWT (HS256) · bcrypt · SQLite (tests)

---

## Installation

```bash
git clone <your-repo-url> CyberVerse-AI
cd CyberVerse-AI
```

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the Vite dev server proxies `/api` to `http://127.0.0.1:8000`.

## Environment variables

Copy [`.env.example`](.env.example).

| Variable | Where | Required | Purpose |
| --- | --- | --- | --- |
| `VITE_API_URL` | frontend | no (prod) | Backend base URL; empty = same-origin `/api` |
| `VITE_POLL_INTERVAL` | frontend | no | Dashboard polling cadence (ms) |
| `DATABASE_URL` | backend | no | `postgresql+psycopg://user:pass@host/db`; empty = in-memory demo mode |
| `AUTH_ENABLED` | backend | no (default `true`) | Enforced only together with `DATABASE_URL` |
| `JWT_SECRET` | backend | **yes in production** | HS256 signing key (≥ 32 chars) |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | backend | prod + auth | First admin account (bcrypt-hashed at boot) |
| `ACCESS_TOKEN_TTL` / `REFRESH_TOKEN_TTL` | backend | no | Token lifetimes, seconds (default 900 / 604800) |
| `AUTH_LOGIN_LIMIT_PER_MINUTE` | backend | no | Failed-login budget per IP (default 10) |
| `AUTH_REQUIRE_READ` | backend | no | Also gate read endpoints behind auth |
| `COOKIES_SECURE` | backend | no | Refresh cookie `Secure` flag (auto in production) |
| `AI_API_KEY` | backend | no | Enables external LLM for the AI analyst |
| `AI_PROVIDER` / `AI_API_BASE` / `AI_MODEL` | backend | no | LLM provider selection (OpenAI-compatible by default) |
| `CORS_ORIGINS` | backend | no | Allowed browser origins (explicit list in production) |
| `RATE_LIMIT_PER_MINUTE` | backend | no | Per-client request budget (default 240) |
| `ENVIRONMENT` | backend | no | `development` / `production` (production enables fail-fast validation) |
| `LOG_FORMAT` / `METRICS_ENABLED` | backend | no | `json`/`text` logs; `/metrics` toggle |

**No secret is ever shipped to the browser.** The frontend only receives the non-sensitive `/api/settings`
document.

## Running locally

| | Command | URL |
| --- | --- | --- |
| Backend | `cd backend && uvicorn app.main:app --reload --port 8000` | http://localhost:8000/api/health |
| Frontend | `cd frontend && npm run dev` | http://localhost:5173 |
| API docs | — | http://localhost:8000/docs |

### Tests

```bash
# backend (47 tests: API, detection, auth/RBAC, database, observability)
cd backend && python -m pytest tests -q

# frontend (15 tests: app + auth flows)
cd frontend && npm run test

# frontend production build
cd frontend && npm run build
```

### One-command stack (Docker Compose)

```bash
# PostgreSQL + API + nginx console (dev defaults; see docs/production.md)
docker compose up --build
# → http://localhost:8080 · login admin@cyberverse.local / cyberverse-admin
```

### PostgreSQL (without Docker)

```bash
# local server, then:
export DATABASE_URL="postgresql+psycopg://cyberverse:secret@localhost:5432/cyberverse"
cd backend && alembic upgrade head && uvicorn app.main:app --reload --port 8000
```

Restart the backend — `/api/health` reports `database: postgresql`. Without
`DATABASE_URL` the API reports `disabled` and runs the full demo from memory.

### AI API setup (optional)

```bash
export AI_PROVIDER=openai
export AI_API_KEY=sk-...
export AI_MODEL=gpt-4o-mini
```
With no key, the AI Analyst uses `local-analysis-engine` — identical section structure, no failures.

## Demo mode

1. Start backend + frontend.
2. Click **[ START HACKATHON DEMO ]** on the Overview page (or **Run Demo** on the landing page).
3. The 12-step sequence runs for ~90 seconds: baseline → recon → credential attack → detection →
   3D threat → incident → attack graph → AI explanation → recommendations.
4. When it reaches **Containment requested**, open the incident and press **[ CONTAIN THREAT ]**.
5. The demo finishes with recovery. Use **Reset** to run it again.

Everything is repeatable; `POST /api/demo/reset` restores baseline telemetry.

## Deployment

### Live (single Vercel project)

| | |
| --- | --- |
| **App** | https://cyberverse-ai.vercel.app |
| **Source** | https://github.com/deepsh3969/CyberVerse-AI (connected to Vercel Git — pushing to `main` redeploys) |

The repository deploys as **one Vercel project** using the FastAPI framework preset, so the console and the
API share a single origin — no `VITE_API_URL` and no CORS configuration:

| Piece | Configuration |
| --- | --- |
| Frontend build | `vercel.json` → `buildCommand` = `npm install --prefix frontend && npm run build --prefix frontend` into `frontend/dist` |
| Python dependencies | FastAPI framework preset auto-detects install: `uv` syncs `[project].dependencies` from `pyproject.toml` (mirrors `requirements.txt`); this keeps Vercel's function-bundle optimization active (225 MB limit) |
| Python entrypoint | `pyproject.toml` → `tool.vercel.entrypoint = "api.index:app"` (wraps `backend/app/main.py`) |
| SPA + API routing | `app.frontend()` in `backend/app/main.py` serves `frontend/dist` with an `index.html` fallback (navigation requests send `Accept: text/html`); API path operations always win |
| Function budget | `vercel.json` → `functions["api/index.py"].maxDuration = 60` + `excludeFiles` (tests/docs/caches) |
| State | in-memory (`AUTH_ENABLED=false` — no database on serverless); Docker Compose is the persistent deployment |

Verified live: `/` (landing), `/app/*` (console), `/api/health`, static assets, `POST /api/simulate/*`,
`POST /api/analyze`, `POST /api/incidents/{id}/contain`, `/api/demo/*`.

### Deploy your own copy

```bash
# with the Vercel CLI (already authenticated)
vercel link --project cyberverse-ai     # or any project name
vercel deploy --prod
```
or import the GitHub repository in the Vercel dashboard (framework: FastAPI, no extra settings needed).

### Alternative: separate frontend / backend hosts

If you prefer split hosting, build the frontend anywhere static and point it at a Python host:

```bash
# backend on Render / Railway / Fly.io
Root directory: backend
Build:  pip install -r requirements.txt
Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
Then set `VITE_API_URL=https://<backend-host>` before building the frontend and allow the frontend origin
with `CORS_ORIGINS` on the backend. Details in [`docs/deployment.md`](docs/deployment.md).

## Screenshots

Add screenshots after running the app locally:

```
docs/screenshots/
  landing.png        – hero with 3D network
  overview.png       – SOC dashboard + storyline ribbon
  network3d.png      – 3D map with a red attack path
  attack-graph.png   – reconstructed lateral path
  ai-analyst.png     – structured incident analysis
  containment.png    – THREAT CONTAINED banner
```

## Repository layout

```
CyberVerse-AI/
├── frontend/          # React + Vite + Tailwind + Three.js
├── backend/           # FastAPI, detection engine, simulator, incidents
│   └── alembic/       # versioned schema migrations (PostgreSQL)
├── ml/                # Training script, scorer, sample data
├── docs/              # architecture, API, demo script, deployment, production runbook
├── .github/workflows/ # CI: pytest + vitest + build + docker images
├── docker-compose.yml # db (PostgreSQL) + api + web (nginx)
├── .env.example
├── LICENSE
└── README.md
```

## Future improvements

- Real WebSocket transport (an SSE endpoint already exists at `/api/events/stream`).
- Sigma/YARA-style rule authoring UI.
- Additional supervised models (Random Forest / XGBoost) with labelled incident history.
- Continuous training loop from analyst feedback.
- Horizontal API scaling (requires shared live-state layer; see `docs/production.md` § 6).

## Team

Built as a hackathon project by a full-stack / AI / security engineering team.
Defensive security research only — see the [LICENSE](LICENSE) and the methodology notes above.
