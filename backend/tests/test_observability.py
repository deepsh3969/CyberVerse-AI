"""Observability: metrics, readiness, request ids, security headers, limits."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_metrics_endpoint(client):
    client.get("/api/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    assert "cyberverse_up 1" in body
    assert "cyberverse_events_total" in body
    assert "http_requests_total{" in body
    assert "http_request_duration_seconds_bucket{" in body


def test_metrics_disabled_returns_404(client):
    previous = settings.metrics_enabled
    settings.metrics_enabled = False
    try:
        assert client.get("/metrics").status_code == 404
    finally:
        settings.metrics_enabled = previous


def test_readiness_reports_disabled_database(client):
    r = client.get("/api/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["database"] == "disabled"
    assert body["checks"]["config"]["problems"] == []
    assert body["checks"]["database"]["status"] == "disabled"


def test_request_id_propagates(client):
    r = client.get("/api/health", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers.get("x-request-id") == "trace-abc-123"
    auto = client.get("/api/health")
    assert len(auto.headers.get("x-request-id", "")) == 16


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["permissions-policy"]


def test_oversized_body_is_rejected(client):
    previous = settings.max_body_bytes
    settings.max_body_bytes = 64
    try:
        r = client.post("/api/analyze", content=b"x" * 128, headers={"content-type": "application/json"})
        assert r.status_code == 413
    finally:
        settings.max_body_bytes = previous


def test_health_shape(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["ml_backend"] == "isolation-forest"
    assert isinstance(body["uptime_seconds"], (int, float))
