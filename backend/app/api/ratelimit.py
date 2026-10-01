"""Sliding-window rate limiting (per client IP).

In-memory by design: each replica protects itself, which is the correct
behaviour for a single-process deployment and a useful safety net when
running multiple replicas behind a load balancer. Swap the storage for Redis
if you need a global budget (see docs/production.md).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

from app.core.config import settings

_VISITS: Dict[str, Deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        real = request.headers.get("x-real-ip", "")
        if real:
            return real.strip()[:64]
    return request.client.host if request.client else "unknown"


def _check(key: str, limit: int) -> None:
    if limit <= 0:
        return
    now = time.time()
    bucket = _VISITS[key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Slow down.")
    bucket.append(now)


def rate_limit(request: Request) -> None:
    _check(f"api:{client_ip(request)}", settings.rate_limit_per_minute)


def rate_limit_login(request: Request) -> None:
    """Stricter budget for credential endpoints (brute-force protection)."""
    _check(f"login:{client_ip(request)}", settings.auth_login_limit_per_minute)


def reset_buckets() -> None:
    """Test helper: clear all counters."""
    _VISITS.clear()
