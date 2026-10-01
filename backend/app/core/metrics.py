"""Dependency-free Prometheus-compatible metrics.

Exposition follows the Prometheus text format so a standard scraper can
consume `/metrics` without this app linking the prometheus_client library
(fewer deps in the function bundle, full control over cardinality).
"""
from __future__ import annotations

import threading
import time
from typing import Iterable

DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def _fmt_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    inner = ",".join(
        f'{k}="{str(v).replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        for k, v in sorted(labels.items())
    )
    return "{" + inner + "}"


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple, float] = {}
        self._gauges: dict[tuple, float] = {}
        self._histograms: dict[tuple, dict] = {}
        self.started_at = time.time()

    # ----------------------------------------------------------------- write
    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, buckets: Iterable[float] = DEFAULT_BUCKETS, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            entry = self._histograms.get(key)
            if entry is None:
                entry = {
                    "buckets": {float(b): 0 for b in buckets},
                    "sum": 0.0,
                    "count": 0,
                }
                self._histograms[key] = entry
            entry["sum"] += value
            entry["count"] += 1
            for bound in entry["buckets"]:
                if value <= bound:
                    entry["buckets"][bound] += 1

    # --------------------------------------------------------------- read
    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = {k: dict(v, buckets=dict(v["buckets"])) for k, v in self._histograms.items()}

        lines.append("# HELP cyberverse_process_uptime_seconds Seconds since process start.")
        lines.append("# TYPE cyberverse_process_uptime_seconds gauge")
        lines.append(f"cyberverse_process_uptime_seconds {time.time() - self.started_at:.3f}")

        by_name: dict[str, list] = {}
        for (name, labels), value in counters.items():
            by_name.setdefault(name, []).append((labels, value))
        for name, entries in sorted(by_name.items()):
            lines.append(f"# TYPE {name} counter")
            for labels, value in sorted(entries):
                lines.append(f"{name}{_fmt_labels(dict(labels))} {value:g}")

        by_name = {}
        for (name, labels), value in gauges.items():
            by_name.setdefault(name, []).append((labels, value))
        for name, entries in sorted(by_name.items()):
            lines.append(f"# TYPE {name} gauge")
            for labels, value in sorted(entries):
                lines.append(f"{name}{_fmt_labels(dict(labels))} {value:g}")

        for (name, labels), entry in sorted(histograms.items()):
            lines.append(f"# TYPE {name} histogram")
            cumulative = 0
            for bound in sorted(entry["buckets"]):
                cumulative = entry["buckets"][bound]
                bucket_labels = dict(labels)
                bucket_labels["le"] = f"{bound:g}"
                lines.append(f"{name}_bucket{_fmt_labels(bucket_labels)} {cumulative}")
            lines.append(f"{name}_bucket{_fmt_labels({**dict(labels), 'le': '+Inf'})} {entry['count']}")
            lines.append(f"{name}_sum{_fmt_labels(dict(labels))} {entry['sum']:g}")
            lines.append(f"{name}_count{_fmt_labels(dict(labels))} {entry['count']}")
        return "\n".join(lines) + "\n"


METRICS = Metrics()
