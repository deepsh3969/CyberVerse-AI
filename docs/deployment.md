# Deployment

## 1. Frontend → Vercel

1. Push the repository to GitHub.
2. Vercel → **Add New → Project** → import `CyberVerse-AI`.
3. Set **Root Directory** to `frontend` (Settings → General → Root Directory).
   Framework preset **Vite** is auto-detected; otherwise set:
   - Build command: `npm run build`
   - Output directory: `dist`
4. Environment variables → add `VITE_API_URL = https://<backend-host>` (no trailing slash).
5. Deploy. `frontend/vercel.json` supplies SPA rewrites, asset caching and security headers.
6. Re-deploy after changing env vars (they are inlined at build time).

Local equivalents:

```bash
cd frontend
npm install
npm run build      # must complete without errors
npm run preview    # sanity-check the production bundle
```

## 2. Backend → a Python host

FastAPI runs as a long-lived process with scikit-learn in memory, so host it on a container/PaaS
service rather than Vercel's default serverless functions.

**Render (example)**

| Field | Value |
| --- | --- |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/api/health` |

**Railway / Fly.io / Cloud Run** — same shape: install requirements, run uvicorn, expose `$PORT`.

Environment variables to set on the backend host:

```
ENVIRONMENT=production
CORS_ORIGINS=https://<your-vercel-domain>
RATE_LIMIT_PER_MINUTE=240
# optional
MONGODB_URI=...
AI_PROVIDER=openai
AI_API_KEY=...
AI_MODEL=gpt-4o-mini
```

Verify after deploy:

```bash
curl https://<backend-host>/api/health
curl https://<backend-host>/api/dashboard
curl -X POST https://<backend-host>/api/simulate/brute-force -H 'content-type: application/json' -d '{}'
```

## 3. Connect the two

1. Set `VITE_API_URL=https://<backend-host>` on Vercel and redeploy the frontend.
2. Set `CORS_ORIGINS=https://<vercel-domain>` on the backend and restart it.
3. Open the Vercel URL → header must show **LIVE** and the dashboard must show live counters.

## 4. Validation checklist

| Check | Command / action |
| --- | --- |
| Frontend builds | `cd frontend && npm install && npm run build` |
| Frontend tests | `cd frontend && npm run test` |
| Backend healthy | `GET /api/health` → `status: ok` |
| Backend tests | `cd backend && python -m pytest tests -q` |
| Simulation | `POST /api/simulate/data-exfiltration` → threat + incident |
| Detection | Threat contains `risk_score`, `confidence`, `evidence` |
| AI analysis | `POST /api/analyze` → sections + recommendations |
| Containment | `POST /api/incidents/{id}/contain` → `THREAT CONTAINED` |
| 3D network | `GET /api/network` → 10 nodes / 14 edges; UI renders |
| Demo mode | `POST /api/demo/start` → 12 steps advance |
| Offline fallback | Stop the backend → frontend shows preview banner and still renders |

## Notes

- The frontend is prepared for Vercel; **the backend is not deployed by this repository** — no backend
  URL is claimed until you complete step 2.
- If you deploy only the frontend, the console runs in preview mode using bundled data.
- Never commit `.env`; use the host's environment variable UI.
