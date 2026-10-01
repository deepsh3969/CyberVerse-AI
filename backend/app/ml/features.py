"""Feature extraction for security events.

Each event is turned into a numeric vector so an Isolation Forest can score it.
Features are computed from rolling context over a short time window.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque

import numpy as np

from app.services import topology

FEATURE_NAMES = [
    "event_frequency",
    "failed_login_count",
    "avg_interval",
    "source_frequency",
    "destination_frequency",
    "request_count",
    "bytes_out",
    "port_spread",
    "access_hour",
    "asset_sensitivity",
    "severity_code",
    "rare_event",
]

LOGIN_FAILURES = {"AUTH_LOGIN_FAILED", "AUTH_PASSWORD_SPRAY", "AUTH_LOCKOUT"}
REQUEST_EVENTS = {"HTTP_REQUEST", "DNS_QUERY", "API_CALL"}


def severity_code(severity: str) -> int:
    return {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(severity, 0)


def hour_of(ts: float) -> float:
    return time.localtime(ts).tm_hour + (time.localtime(ts).tm_min / 60.0)


def cycle_encode(value: float, period: float) -> tuple[float, float]:
    """Encode a cyclic quantity (hour of day) without a discontinuity."""
    angle = 2 * math.pi * (value % period) / period
    return math.sin(angle), math.cos(angle)


class FeatureBuilder:
    """Stateful builder: feed events in chronological order, get vectors."""

    def __init__(self, window_seconds: float = 900.0) -> None:
        self.window = window_seconds
        self.types: dict[str, deque] = defaultdict(lambda: deque())
        self.sources: dict[str, deque] = defaultdict(lambda: deque())
        self.dests: dict[str, deque] = defaultdict(lambda: deque())
        self.logins: dict[str, deque] = defaultdict(lambda: deque())
        self.requests: dict[str, deque] = defaultdict(lambda: deque())
        self.ports: dict[str, set] = defaultdict(set)
        self.rare_types: set[str] = set()
        self.seen_counts: dict[str, int] = defaultdict(int)
        self.total = 0

    def _trim(self, bucket: dict, key: str, now: float) -> None:
        dq = bucket[key]
        while dq and now - dq[0] > self.window:
            dq.popleft()

    def vector(self, event: dict) -> np.ndarray:
        now = float(event.get("timestamp", time.time()))
        etype = event.get("event_type", "")
        src = event.get("source", "")
        dst = event.get("destination", "")
        meta = event.get("metadata") or {}

        self._trim(self.types, etype, now)
        self._trim(self.sources, src, now)
        self._trim(self.dests, dst, now)
        self._trim(self.logins, src, now)
        self._trim(self.requests, dst, now)

        self.types[etype].append(now)
        self.sources[src].append(now)
        self.dests[dst].append(now)
        self.seen_counts[etype] += 1
        self.total += 1

        if etype in LOGIN_FAILURES:
            self.logins[src].append(now)
        if etype in REQUEST_EVENTS:
            self.requests[dst].append(now)
        if "port" in meta:
            self.ports[src].add(int(meta["port"]))
        elif etype == "NETWORK_PORT_SCAN":
            self.ports[src].add(int(meta.get("port", 0)))

        dq = self.sources[src]
        intervals = [dq[i + 1] - dq[i] for i in range(len(dq) - 1)]
        avg_interval = float(np.mean(intervals)) if intervals else self.window

        event_frequency = len(self.types[etype])
        failed_login_count = len(self.logins[src])
        source_frequency = len(dq)
        destination_frequency = len(self.dests[dst])
        request_count = len(self.requests[dst])
        bytes_out = float(meta.get("bytes_out", 0))
        port_spread = float(len(self.ports[src]))
        access_hour = hour_of(now)
        node = topology.get_node(dst) or {}
        node_id = node.get("id", dst)
        asset_sensitivity = float(topology.ASSET_SENSITIVITY.get(node_id, 40))
        sev = severity_code(event.get("severity", "INFO"))
        rare = 1.0 if self.seen_counts[etype] <= 2 and self.total > 30 else 0.0
        hour_sin, hour_cos = cycle_encode(access_hour, 24.0)

        vec = np.array(
            [
                min(event_frequency, 60) / 60.0,
                min(failed_login_count, 50) / 50.0,
                min(avg_interval, self.window) / self.window,
                min(source_frequency, 80) / 80.0,
                min(destination_frequency, 80) / 80.0,
                min(request_count, 400) / 400.0,
                min(math.log10(bytes_out + 1), 9) / 9.0,
                min(port_spread, 40) / 40.0,
                hour_sin,
                hour_cos,
                asset_sensitivity / 100.0,
                sev / 4.0,
                rare,
            ],
            dtype=np.float64,
        )
        return vec

    def context(self, event: dict) -> dict:
        now = float(event.get("timestamp", time.time()))
        src = event.get("source", "")
        dst = event.get("destination", "")
        etype = event.get("event_type", "")
        return {
            "event_frequency": len(self.types[etype]),
            "failed_login_count": len(self.logins[src]),
            "source_frequency": len(self.sources[src]),
            "destination_frequency": len(self.dests[dst]),
            "request_count": len(self.requests[dst]),
            "port_spread": len(self.ports[src]),
            "hour": hour_of(now),
        }


def synthetic_normal_dataset(n: int = 2600, seed: int = 42) -> np.ndarray:
    """Procedurally generated baseline of benign activity for unsupervised training."""
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n):
        event_frequency = rng.gamma(2.0, 0.06)
        failed = rng.beta(1.1, 14.0)
        avg_interval = rng.beta(5.0, 2.0)
        source_freq = rng.gamma(2.2, 0.05)
        dest_freq = rng.gamma(2.0, 0.05)
        request_count = rng.gamma(1.8, 0.05)
        bytes_out = rng.beta(1.4, 6.0)
        port_spread = rng.beta(1.2, 8.0)
        hour = rng.uniform(0, 24)
        hour_sin, hour_cos = cycle_encode(hour, 24.0)
        sensitivity = rng.beta(2.0, 3.0) * 0.9 + 0.05
        severity = rng.choice([0, 0, 0, 1, 1, 2], p=[0.4, 0.25, 0.15, 0.1, 0.07, 0.03])
        rare = 0.0 if rng.random() > 0.04 else 1.0
        samples.append(
            [
                min(event_frequency, 1.6),
                failed,
                avg_interval,
                min(source_freq, 1.5),
                min(dest_freq, 1.5),
                min(request_count, 1.4),
                bytes_out,
                min(port_spread, 0.8),
                hour_sin,
                hour_cos,
                sensitivity,
                severity / 4.0,
                rare,
            ]
        )
    return np.asarray(samples, dtype=np.float64)
