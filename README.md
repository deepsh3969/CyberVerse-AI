# CYBERVERSE AI

**AI-Powered 3D Cybersecurity Command Center**

> SEE THE ATTACK. UNDERSTAND THE THREAT. STOP IT.

CyberVerse AI simulates a company's digital infrastructure, generates safe synthetic cyber events, detects
and classifies threats with a local ML engine, explains them with an AI analyst, reconstructs the attack
path in 3D, and lets an analyst contain the threat — all inside a defensive sandbox.

![status](https://img.shields.io/badge/status-working%20prototype-blue) ![frontend](https://img.shields.io/badge/frontend-React%20%2B%20Three.js-38d6f5) ![backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20scikit--learn-ff3b5c)

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
| **Resilience** | Backend offline → bundled preview data + clear banner; invalid responses, timeouts and missing config all degrade gracefully |

## Architecture

```
┌──────────────────────────────┐        ┌─────────────────────────────────────┐
│  frontend/  (React + Vite)   │  HTTP  │  backend/  (FastAPI)                │
│  ─ Landing / Command Center  │◄──────►│  ─ REST API  /api/*                 │
│  ─ 3D network (R3F/Three)    │  JSON  │  ─ Simulator (8 synthetic scripts)  │
│  ─ Charts (Recharts)         │        │  ─ Feature extraction               │
│  ─ State + polling + fallback│        │  ─ Isolation Forest + rule engine   │
└──────────────────────────────┘        │  ─ Incident / graph / containment   │
                                        │  ─ AI analyst (local or LLM)        │
                                        │  ─ In-memory store ⇄ MongoDB        │
                                        └──────────────────┬──────────────────┘
                                                           │ optional
                                                ┌──────────▼──────────┐
                                                │  MongoDB (persist)  │
                                                └─────────────────────┘
```

Detailed documents: [`docs/architecture.md`](docs/architecture.md) ·
[`docs/api.md`](docs/api.md) · [`docs/deployment.md`](docs/deployment.md) ·
[`docs/demo-script.md`](docs/demo-script.md)

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

**Database:** MongoDB (optional) with automatic in-memory demo fallback

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
| `MONGODB_URI` | backend | no | Enables MongoDB persistence; empty = in-memory demo mode |
| `MONGODB_DB` | backend | no | Database name (default `cyberverse`) |
| `AI_API_KEY` | backend | no | Enables external LLM for the AI analyst |
| `AI_PROVIDER` / `AI_API_BASE` / `AI_MODEL` | backend | no | LLM provider selection (OpenAI-compatible by default) |
| `CORS_ORIGINS` | backend | no | Allowed browser origins |
| `RATE_LIMIT_PER_MINUTE` | backend | no | Per-client request budget (default 240) |
| `ENVIRONMENT` | backend | no | `development` / `production` |

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
# backend (20 tests)
cd backend && python -m pytest tests -q

# frontend (6 tests)
cd frontend && npm run test

# frontend production build
cd frontend && npm run build
```

### MongoDB setup (optional)

```bash
# local
mongod --dbpath ./data
# or free tier Atlas, then:
export MONGODB_URI="mongodb+srv://user:pass@cluster0.mongodb.net/cyberverse"
```
Restart the backend — `/api/health` reports `database: mongodb`. Without it the API reports `disabled`
and still runs the full demo from memory.

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

### Frontend — Vercel

1. Push the repository to GitHub.
2. Vercel → **Add New Project** → import the repo → set **Root Directory** to `frontend`
   (framework preset: Vite, build `npm run build`, output `dist`).
3. Add env var `VITE_API_URL=https://<your-backend-host>`.
4. Deploy. `frontend/vercel.json` already provides SPA rewrites.

### Backend

FastAPI cannot run on Vercel's default serverless functions in this configuration (long-running process +
scikit-learn), so host it on a Python platform, e.g. **Render / Railway / Fly.io / Hugging Face Spaces**:

```bash
# Render web service
Root directory: backend
Build:  pip install -r requirements.txt
Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
Set `CORS_ORIGINS=https://<your-vercel-domain>` on the backend, then set the same origin in
`VITE_API_URL` on Vercel. See [`docs/deployment.md`](docs/deployment.md).

> The frontend is configured for Vercel; the backend is **not** deployed from this repository by default —
> no backend URL is claimed here.

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
├── ml/                # Training script, scorer, sample data
├── docs/              # architecture, API, demo script, deployment
├── .env.example
├── LICENSE
└── README.md
```

## Future improvements

- Real WebSocket transport (an SSE endpoint already exists at `/api/events/stream`).
- Multi-analyst auth, roles and audit trails.
- Sigma/YARA-style rule authoring UI.
- Additional supervised models (Random Forest / XGBoost) with labelled incident history.
- Continuous training loop from analyst feedback.
- Containerisation (Docker Compose) for one-command local runs.

## Team

Built as a hackathon project by a full-stack / AI / security engineering team.
Defensive security research only — see the [LICENSE](LICENSE) and the methodology notes above.
