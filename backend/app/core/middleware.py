"""Request-scoped middleware: correlation id, access log, metrics, hardening.

Implemented as pure ASGI (not BaseHTTPMiddleware) so streaming responses
(SSE) and long-polling are not buffered or broken.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable, Iterable

from app.core.config import settings
from app.core.logging import request_id_var
from app.core.metrics import METRICS

logger = logging.getLogger("cyberverse.access")

SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"x-dns-prefetch-control", b"off"),
]
HSTS_HEADER = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]


def _request_id(scope: Scope) -> str:
    for key, value in scope.get("headers", []):
        if key == b"x-request-id":
            candidate = value.decode("latin-1").strip()[:64]
            if candidate:
                return candidate
    return uuid.uuid4().hex[:16]


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None) if route is not None else None
    if path:
        return str(path)
    return "unmatched"


class RequestContextMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        token = request_id_var.set(request_id)
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        # ---------------------------------------------------- request guards
        content_length = 0
        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    content_length = int(value)
                except ValueError:
                    content_length = 0
                break
        if content_length > settings.max_body_bytes:
            await self._reject(send, request_id)
            request_id_var.reset(token)
            return

        state = {"status": 500}
        extra = [(b"x-request-id", request_id.encode("latin-1"))]
        extra.extend(SECURITY_HEADERS)
        if settings.is_production:
            extra.append(HSTS_HEADER)

        async def send_wrapper(message: dict) -> None:
            if message.get("type") == "http.response.start":
                state["status"] = message.get("status", 500)
                headers = list(message.get("headers", []))
                present = {k for k, _ in headers}
                headers.extend((k, v) for k, v in extra if k not in present)
                message["headers"] = headers
            await send(message)

        started = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - started
            route = _route_template(scope)
            status = state["status"]
            if settings.metrics_enabled:
                METRICS.inc(
                    "http_requests_total",
                    method=method,
                    route=route,
                    status=str(status),
                )
                METRICS.observe(
                    "http_request_duration_seconds",
                    duration,
                    method=method,
                    route=route,
                )
            if not path.startswith("/metrics"):
                logger.info(
                    "%s %s %s %.1fms",
                    method,
                    path,
                    status,
                    duration * 1000,
                    extra={
                        "http_method": method,
                        "http_path": path,
                        "http_status": status,
                        "duration_ms": round(duration * 1000, 2),
                        "route": route,
                    },
                )
            request_id_var.reset(token)

    @staticmethod
    async def _reject(send: Send, request_id: str) -> None:
        body = b'{"detail":"Request body too large"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                    (b"x-request-id", request_id.encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
