# Production runbook

How to run CyberVerse AI as an industrial-grade service: Docker Compose with
PostgreSQL, JWT auth with roles, audit trails, metrics, migrations, and a
fail-fast configuration check.

---

## 1. Quick start (local, dev defaults)

```bash
docker compose up --build
# → console: http://localhost:8080   ·   API: http://localhost:8000
# → login:   admin@cyberverse.local / cyberverse-admin   (DEV ONLY default)
```

Compose starts three services:

| Service | Image | Port | Purpose |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | internal | PostgreSQL with a named volume `pgdata` |
| `api` | `./backend` (multi-stage not needed) | 8000 | FastAPI + detection engine, runs Alembic-safe schema bootstrap |
| `web` | `./frontend` (node build → nginx) | 8080 | SPA + reverse proxy for `/api` |

## 2. Production checklist

Set these in a `.env` file next to `docker-compose.yml` (Compose reads it automatically):

```bash
ENVIRONMENT=production
JWT_SECRET=<openssl rand -base64 48 — at least 32 chars>
SEED_ADMIN_EMAIL=admin@your-org.example
SEED_ADMIN_PASSWORD=<strong unique password>
CORS_ORIGINS=https://console.your-org.example
POSTGRES_PASSWORD=<strong unique database password>
COOKIES_SECURE=true          # only when served over TLS
```

With `ENVIRONMENT=production` the API **refuses to start** (exit on startup) if any
required value is missing or weak — see `validate()` in `backend/app/core/config.py`:

- `JWT_SECRET` set explicitly, ≥ 32 characters
- `DATABASE_URL` set (auth cannot exist without a database)
- `SEED_ADMIN_PASSWORD` set when `AUTH_ENABLED=true`
- `CORS_ORIGINS` lists explicit origins (no `*`)

Then:

```bash
docker compose up --build -d
docker compose ps          # db: healthy, api: healthy, web: healthy
```

### TLS

Terminate TLS in front of `web` (port 8080) and `api` (port 8000) — Caddy, Traefik,
nginx, or a cloud load balancer. Behind TLS set `COOKIES_SECURE=true` so the refresh
cookie is only sent over HTTPS, and keep `TRUST_PROXY=true` (default) so client IPs in
rate limits and audit logs come from `X-Forwarded-For`.

## 3. Authentication & roles

Auth activates only when **both** `AUTH_ENABLED=true` and `DATABASE_URL` are set
(`settings.auth_active`). Without a database the API runs in open demo mode — the
Vercel deployment does exactly this.

| Role | Can do |
| --- | --- |
| `viewer` | Read dashboards, incidents, events (unless `AUTH_REQUIRE_READ=true`, which also gates reads) |
| `analyst` | Everything a viewer can + simulate, analyze, contain, status changes, demo control |
| `admin` | Everything + `POST /api/reset`, user management, `GET /api/audit` |

Token model:

- **Access token** — JWT (HS256), 15 min (`ACCESS_TOKEN_TTL`), sent as `Authorization: Bearer …`.
- **Refresh token** — opaque random string, 7 days (`REFRESH_TOKEN_TTL`), stored **SHA-256 hashed**
  in PostgreSQL, delivered as an `HttpOnly; SameSite=Lax` cookie (`cv_rt`, path `/api/auth`).
  `POST /api/auth/refresh` rotates it: old row revoked, new cookie issued.
- First boot seeds `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` (bcrypt, `BCRYPT_ROUNDS=12`).
- Login attempts are limited per IP (`AUTH_LOGIN_LIMIT_PER_MINUTE`, default 10/min).

Frontend behavior (`frontend/src/services/api.js`): the SPA keeps the access token in
memory, retries a failed request once after a silent refresh, and emits
`AUTH_EXPIRED_EVENT` → redirect to `/login` when the refresh itself fails.

## 4. Database & migrations

- Engine: **SQLAlchemy 2** on PostgreSQL (`postgresql+psycopg://…`) in production,
  SQLite in tests. Models are in `backend/app/db/models.py`.
- On startup the API creates missing tables when `DB_AUTOCREATE=true` (default),
  hydrates events/threats/incidents/graphs into the in-memory store, then seeds the
  admin user.
- **Alembic** lives in `backend/alembic/`; initial revision
  `7a79fa448df4_initial_schema` covers users, refresh tokens, events, threats,
  incidents, attack graphs, audit logs.

```bash
cd backend

# render the SQL without connecting (validated against PostgreSQL dialect)
ALEMBIC_DATABASE_URL="postgresql+psycopg://user:pass@db:5432/cyberverse" \
  alembic upgrade --sql head

# apply for real
DATABASE_URL="postgresql+psycopg://user:pass@db:5432/cyberverse" alembic upgrade head

# future schema changes
alembic revision --autogenerate -m "describe change"
```

> Note: Alembic migrations and `DB_AUTOCREATE` both work; use migrations when you
> need versioned schema history, autocreate for first-boot convenience. They are
> idempotent with respect to each other (same models).

### Backup / restore

```bash
docker compose exec db pg_dump -U cyberverse cyberverse > backup.sql
docker compose exec -T db psql -U cyberverse cyberverse < backup.sql
```

## 5. Observability

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness — always 200 while the process serves traffic |
| `GET /api/ready` | Readiness — 503 until the DB ping succeeds (use for LB gates) |
| `GET /metrics` | Prometheus text format: request counts/latency histograms, logins, simulations, DB state. Exposed on the API tier only (nginx returns 404 for `/metrics`) |
| `GET /api/audit` | Recent audit trail (admin only) — actor, action, resource, IP, payload |

Logs: structured JSON in production (`LOG_FORMAT=json`), human text in development.
Every request carries an `X-Request-ID` (accepted from the proxy or generated) that
appears in access logs. Security headers (`X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy`, HSTS in production) are added by middleware.

Audit events are recorded for logins, refresh/logout, user CRUD, containment, status
changes, demo start/reset and sandbox reset.

## 6. Scaling notes (honest limitations)

- **One API worker per container.** The live event/threat view is an in-process
  store hydrated from PostgreSQL; multiple uvicorn workers or replicas would each
  hold their own copy. Scale horizontally only if you accept per-replica view
  divergence, or put a single replica behind the load balancer.
- Rate limiting and demo state are also per-process — same constraint.
- PostgreSQL is the source of truth: restarts lose nothing (hydration replays
  recent events, all incidents, graphs, users, audit rows).
- The SSE stream works through the bundled nginx (`proxy_buffering off`), but the
  console polls by default (`VITE_POLL_INTERVAL`).

## 7. Verification (what was actually run)

| Check | Command | Result |
| --- | --- | --- |
| Backend suite | `cd backend && python -m pytest tests -q` | 47 passed |
| Frontend unit tests | `cd frontend && npm run test` | 15 passed |
| Frontend build | `cd frontend && npm run build` | success |
| Compose + CI YAML | parsed with PyYAML | valid |
| Alembic on SQLite | `alembic upgrade head` | tables created |
| Alembic for PostgreSQL | `alembic upgrade --sql head` | renders PG DDL (offline dialect) |
| Live API smoke | `uvicorn app.main:app` + SQLite, 15-check script: health/ready/metrics, 401 on unauthenticated write, 401 on bad login, admin login + `cv_rt` cookie, authenticated simulate, refresh rotation, audit entries + 401 anonymous, viewer read + 403 on admin route, refresh revoked after logout | 15/15 passed |

**Not run in this environment:** actual `docker build` / `docker compose up` and a
real PostgreSQL server — Docker and psql are unavailable on the development machine.
The Dockerfiles, Compose file, and SQL were validated statically only; run
`docker compose up --build` on a Docker host as the first real-hardware check.

## 8. Vercel demo

The public demo (https://cyberverse-ai.vercel.app) runs serverless with
`AUTH_ENABLED=false` (set via `vercel env add AUTH_ENABLED false production`) so the
console works without a database. See `docs/deployment.md`.
