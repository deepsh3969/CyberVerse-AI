# CyberVerse AI — Backend

FastAPI service providing the detection engine, safe attack simulator, incident store, attack graphs,
AI analyst and reporting endpoints.

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://127.0.0.1:8000/api/health`
- Interactive docs: `http://127.0.0.1:8000/docs`

## Tests

```bash
python -m pytest tests -q
```

`tests/live_check.py` boots a real uvicorn process, runs the scripted demo end to end and verifies
containment:

```bash
python -m tests.live_check
```

## Layout

```
app/
├── api/routes.py         # all HTTP endpoints + rate limiting
├── core/config.py        # env-driven settings (no hard-coded secrets)
├── models/schemas.py     # Pydantic request/response contracts
├── ml/
│   ├── features.py       # 13-dimensional event feature extraction
│   └── detector.py       # Isolation Forest + rule engine fusion
├── simulator/scenarios.py# 8 synthetic attack scripts (safe by construction)
├── services/
│   ├── topology.py       # sandbox network definition
│   ├── store.py          # in-memory state ⇄ optional MongoDB mirror
│   ├── engine.py         # orchestration: simulate → detect → incident → graph
│   ├── analyst.py        # local analysis engine + optional LLM
│   └── demo.py           # scripted hackathon walkthrough
└── main.py               # app factory, CORS, error handlers, lifespan
```

## Behaviour notes

- **Demo mode is the default.** If `MONGODB_URI` is unset (or MongoDB is unreachable) the API runs
  entirely from memory and reports `database: disabled`.
- **The AI analyst never fails.** Missing/invalid `AI_API_KEY` falls back to the local engine.
- **Rate limiting** returns `429` above `RATE_LIMIT_PER_MINUTE` per client.
- **All simulated attacks** are generated in-process; no outbound traffic is produced.
