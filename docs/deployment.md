# Deployment

## What is deployed

A **single Vercel project** (framework preset: FastAPI) serves both tiers from one origin:

```
https://cyberverse-ai.vercel.app
├── /                → React landing page (frontend/dist/index.html)
├── /app/*           → command center (SPA fallback: index.html)
├── /assets/*        → hashed JS/CSS bundles
└── /api/*           → FastAPI (api/index.py → backend/app/main.py)
```

- Repository: https://github.com/deepsh3969/CyberVerse-AI
- Live app: https://cyberverse-ai.vercel.app
- The GitHub repo is connected to Vercel Git, so every push to `main` triggers a production deployment.

## Configuration

| File | Purpose |
| --- | --- |
| `vercel.json` | `installCommand` = npm deps + `pip install -r requirements.txt`; `buildCommand` = `npm run build --prefix frontend`; `outputDirectory` = `frontend/dist`; `functions["api/index.py"].maxDuration` = 60; security/caching headers |
| `pyproject.toml` | `tool.vercel.entrypoint = "api.index:app"` |
| `api/index.py` | Serverless wrapper: puts `backend/` on `sys.path`, seeds the engine, repairs a runtime that strips the `/api` prefix, exports the ASGI app |
| `requirements.txt` | Lean serverless dependency set (no pandas/uvicorn/pytest) |
| `.vercelignore` | Keeps `.git`, `.venv`, `node_modules`, `dist`, model artifacts out of the upload |
| `backend/app/main.py` | `app.frontend("/", directory="frontend/dist", fallback="index.html")` — API routes win, navigation requests fall back to the SPA shell |

`frontend/vercel.json` is only used if you deploy the frontend on its own (root directory `frontend`).

## Environment variables

None are required for the default demo (same-origin API). Optional, set in Vercel → Project → Settings →
Environment Variables:

| Name | Effect |
| --- | --- |
| `MONGODB_URI` / `MONGODB_DB` | Persist telemetry and incidents in MongoDB; otherwise in-memory demo mode |
| `AI_API_KEY` / `AI_PROVIDER` / `AI_API_BASE` / `AI_MODEL` | External LLM for the AI analyst (local engine is the default) |
| `CORS_ORIGINS` | Only needed if you split the frontend onto another domain |
| `RATE_LIMIT_PER_MINUTE` | Per-client request budget |

Build-time variables (`VITE_*`) are inlined at build; after changing one, redeploy.

## Deploying

```bash
vercel link --project cyberverse-ai   # first time only
vercel deploy --prod                  # manual
git push origin main                  # or via the connected GitHub repo
```

## Alternative: split hosting

**Backend** on Render / Railway / Fly.io:

```
Root directory: backend
Build:  pip install -r requirements.txt
Start:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Frontend** anywhere static (Vercel, Netlify, GitHub Pages) with
`VITE_API_URL=https://<backend-host>` set before `npm run build`, and
`CORS_ORIGINS=https://<frontend-host>` on the backend.

## Validation checklist

| Check | How |
| --- | --- |
| Landing page | `GET /` → `200 text/html` |
| Deep link | `GET /app/incidents` → `200 text/html` (SPA fallback) |
| API alive | `GET /api/health` → `{"status":"ok", ...}` |
| Static assets | `GET /assets/<hash>.js` → `200 text/javascript` |
| Detection | `POST /api/simulate/data-exfiltration` → threat + incident + graph |
| AI analysis | `POST /api/analyze` → sections + recommendations |
| Containment | `POST /api/incidents/{id}/contain` → `THREAT CONTAINED` |
| Demo | `POST /api/demo/start` → steps advance; `POST /api/demo/stop` then `POST /api/demo/reset` |
| Local tests | `backend: python -m pytest tests -q` (20) · `frontend: npm run test` (6) · `npm run build` |

## Operational notes

- **State is per function instance.** The demo stores everything in memory; a cold start reseeds the
  baseline. For a multi-user deployment add `MONGODB_URI` so every instance shares state.
- **SSE** (`/api/events/stream`) is secondary — the console polls by default, which is the reliable path
  on serverless.
- **Rate limiting** is per instance and in-memory.
- Everything is synthetic: no outbound scanning, exploitation or credential use is performed anywhere.
