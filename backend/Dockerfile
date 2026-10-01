# syntax=docker/dockerfile:1
# CyberVerse AI backend API (FastAPI + SQLAlchemy).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/cyberverse

# Run as an unprivileged user.
RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

USER app
EXPOSE 8000

# Liveness: /api/health answers 200 whenever the process can serve traffic.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request as u, sys; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# --proxy-headers makes rate limiting and audit logs see the real client IP
# when running behind the nginx tier / a load balancer.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
