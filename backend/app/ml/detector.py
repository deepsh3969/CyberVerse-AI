"""Hybrid threat detection: rule engine + Isolation Forest anomaly scoring.

The rule engine provides deterministic, explainable detections (essential for a
reliable live demo). The Isolation Forest provides unsupervised anomaly scores
that modulate confidence and risk. Both run locally with no external service.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from app.ml.features import FEATURE_NAMES, FeatureBuilder, hour_of, synthetic_normal_dataset
from app.models.schemas import Severity, Threat
from app.services import topology
from app.services.store import new_id

BASELINE_TITLES = {"HEARTBEAT", "HTTP_REQUEST", "DNS_QUERY", "API_CALL", "AUTH_LOGIN_SUCCESS", "AUTH_LOGOUT"}

RULES: dict[str, dict[str, Any]] = {
    "PORT_SCAN": {
        "threat_type": "Port Scan",
        "base_severity": Severity.MEDIUM,
        "base_risk": 58,
        "min_count": 8,
        "path": ["attacker", "internet", "firewall", "web"],
        "prevention": "Rate-limit recon traffic at the perimeter and enable automatic IP reputation blocking.",
    },
    "BRUTE_FORCE": {
        "threat_type": "Brute Force",
        "base_severity": Severity.HIGH,
        "base_risk": 78,
        "min_count": 5,
        "path": ["attacker", "internet", "vpn", "firewall", "auth", "account", "db"],
        "prevention": "Enforce MFA, exponential login backoff and source blocking after repeated failures.",
    },
    "SUSPICIOUS_LOGIN": {
        "threat_type": "Suspicious Login",
        "base_severity": Severity.MEDIUM,
        "base_risk": 62,
        "min_count": 1,
        "path": ["attacker", "internet", "vpn", "auth", "account"],
        "prevention": "Require step-up authentication for impossible-travel and new-device sign-ins.",
    },
    "PRIVILEGE_ESCALATION": {
        "threat_type": "Privilege Escalation",
        "base_severity": Severity.HIGH,
        "base_risk": 82,
        "min_count": 1,
        "path": ["attacker", "internet", "firewall", "web", "api", "account"],
        "prevention": "Remove standing admin rights, audit sudo rules and alert on privilege changes.",
    },
    "DATA_EXFILTRATION": {
        "threat_type": "Data Exfiltration",
        "base_severity": Severity.CRITICAL,
        "base_risk": 92,
        "min_count": 1,
        "path": ["attacker", "internet", "firewall", "web", "api", "db"],
        "prevention": "Block large outbound transfers, enable DLP inspection and rotate exposed credentials.",
    },
    "MALWARE": {
        "threat_type": "Malware Activity",
        "base_severity": Severity.CRITICAL,
        "base_risk": 88,
        "min_count": 1,
        "path": ["attacker", "internet", "firewall", "web", "api"],
        "prevention": "Isolate the endpoint, quarantine the file and run a full endpoint scan.",
    },
    "DDOS": {
        "threat_type": "DDoS Traffic Spike",
        "base_severity": Severity.HIGH,
        "base_risk": 74,
        "min_count": 1,
        "path": ["botnet", "internet", "firewall", "web"],
        "prevention": "Activate traffic scrubbing, scale out the web tier and lower the per-IP request cap.",
    },
    "INSIDER": {
        "threat_type": "Insider Threat",
        "base_severity": Severity.HIGH,
        "base_risk": 80,
        "min_count": 1,
        "path": ["insider", "users", "vpn", "auth", "db"],
        "prevention": "Suspend the account, review data access history and enforce least privilege.",
    },
}

SEVERITY_ORDER = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


def max_severity(a: Severity, b: Severity) -> Severity:
    return a if SEVERITY_ORDER.index(a) >= SEVERITY_ORDER.index(b) else b


class ThreatDetector:
    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.backend = "warming up"
        self.feature_names = FEATURE_NAMES
        self._train()

    # ----------------------------------------------------------------- training
    def _train(self, extra_vectors: Optional[np.ndarray] = None) -> None:
        data = synthetic_normal_dataset()
        if extra_vectors is not None and len(extra_vectors):
            data = np.vstack([data, extra_vectors])
        model = IsolationForest(
            n_estimators=140,
            contamination=0.045,
            max_samples="auto",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(data)
        self.model = model
        self.backend = "isolation-forest"
        try:
            import joblib

            path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ml", "models", "isolation_forest.joblib")
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
            joblib.dump(model, path)
        except Exception:
            pass

    def load_or_train(self, events: list[dict]) -> None:
        """Retrain using observed benign traffic as extra baseline context."""
        builder = FeatureBuilder()
        vectors = []
        for ev in sorted(events, key=lambda e: e.get("timestamp", 0)):
            if ev.get("event_type") in BASELINE_TITLES:
                vectors.append(builder.vector(ev))
        self._train(np.vstack(vectors) if vectors else None)

    # ------------------------------------------------------------------ scoring
    def anomaly_score(self, vector: np.ndarray) -> float:
        if self.model is None:
            return 0.5
        decision = float(self.model.decision_function(vector.reshape(1, -1))[0])
        return float(np.clip(0.5 - decision, 0.0, 1.0))

    def scores_for(self, vectors: list[np.ndarray]) -> list[float]:
        return [self.anomaly_score(v) for v in vectors]

    # ---------------------------------------------------------------- detection
    def detect(
        self,
        events: list[dict],
        vectors: list[np.ndarray],
        contexts: list[dict],
    ) -> list[dict[str, Any]]:
        """Return detection candidates (rule hits enriched with ML scores)."""
        if not events:
            return []
        by_type: dict[str, list[int]] = {}
        for idx, ev in enumerate(events):
            by_type.setdefault(ev["event_type"], []).append(idx)

        candidates: list[dict[str, Any]] = []
        candidates.extend(self._rule_brute_force(events, vectors, contexts))
        candidates.extend(self._rule_port_scan(events, vectors, contexts))
        candidates.extend(self._rule_single(events, vectors, contexts))
        return candidates

    # -------------------------------------------------------------------- rules
    def _ml_confidence(self, idxs: list[int], vectors: list[np.ndarray]) -> tuple[float, float]:
        if not idxs or not vectors:
            return 0.0, 0.0
        vals = [self.anomaly_score(vectors[i]) for i in idxs if i < len(vectors)]
        if not vals:
            return 0.0, 0.0
        return float(np.mean(vals)), float(np.max(vals))

    def _rule_brute_force(self, events, vectors, contexts) -> list[dict]:
        failures: dict[tuple, list[int]] = {}
        for i, ev in enumerate(events):
            if ev["event_type"] in ("AUTH_LOGIN_FAILED", "AUTH_PASSWORD_SPRAY"):
                failures.setdefault((ev["source"], ev["destination"]), []).append(i)
        out = []
        rule = RULES["BRUTE_FORCE"]
        for (src, dst), idxs in failures.items():
            if len(idxs) < rule["min_count"]:
                continue
            success_idx = [
                i
                for i, ev in enumerate(events)
                if ev["event_type"] == "AUTH_LOGIN_SUCCESS"
                and ev["source"] == src
                and ev["destination"] == dst
                and i > idxs[-1]
                and float(ev["timestamp"]) - float(events[idxs[-1]]["timestamp"]) < 120
            ]
            mean_anom, max_anom = self._ml_confidence(idxs + success_idx, vectors)
            evidence = [f"{len(idxs)} failed login attempts from {src} to {dst}"]
            if success_idx:
                evidence.append("Successful login immediately after repeated failures")
            evidence.append(f"Burst window under {int(events[success_idx[-1] if success_idx else idxs[-1]]['timestamp'] - events[idxs[0]]['timestamp'])}s")
            if mean_anom > 0.55:
                evidence.append("Isolation Forest flagged the sequence as an outlier (score %.2f)" % mean_anom)
            confidence = 0.86 + (0.09 if success_idx else 0.0) + min(0.04, mean_anom * 0.05)
            out.append(
                {
                    "rule": "BRUTE_FORCE",
                    "event_idxs": idxs + success_idx,
                    "source": src,
                    "destination": dst,
                    "evidence": evidence,
                    "confidence": min(0.99, confidence),
                    "anomaly": mean_anom,
                    "max_anomaly": max_anom,
                    "count": len(idxs),
                }
            )
        return out

    def _rule_port_scan(self, events, vectors, contexts) -> list[dict]:
        ports: dict[str, set] = {}
        idxs_map: dict[str, list[int]] = {}
        for i, ev in enumerate(events):
            if ev["event_type"] == "NETWORK_PORT_SCAN":
                port = int((ev.get("metadata") or {}).get("port", 0))
                ports.setdefault(ev["source"], set()).add(port)
                idxs_map.setdefault(ev["source"], []).append(i)
        rule = RULES["PORT_SCAN"]
        out = []
        for src, portset in ports.items():
            idxs = idxs_map[src]
            if len(portset) < rule["min_count"]:
                continue
            dst = events[idxs[-1]]["destination"]
            mean_anom, max_anom = self._ml_confidence(idxs, vectors)
            evidence = [
                f"{len(portset)} distinct ports probed from {src}",
                f"Sequential service enumeration against {dst}",
                "Reconnaissance pattern consistent with pre-exploitation scanning",
            ]
            if mean_anom > 0.5:
                evidence.append("Anomaly score %.2f on scan bursts" % mean_anom)
            out.append(
                {
                    "rule": "PORT_SCAN",
                    "event_idxs": idxs,
                    "source": src,
                    "destination": dst,
                    "evidence": evidence,
                    "confidence": min(0.98, 0.82 + min(0.12, mean_anom * 0.2)),
                    "anomaly": mean_anom,
                    "max_anomaly": max_anom,
                    "count": len(idxs),
                }
            )
        return out

    def _rule_single(self, events, vectors, contexts) -> list[dict]:
        mapping = {
            "PRIVILEGE_ESCALATION": "PRIVILEGE_ESCALATION",
            "DATA_EXFILTRATION": "DATA_EXFILTRATION",
            "MALWARE_FILE_ACTIVITY": "MALWARE",
            "NETWORK_TRAFFIC_SPIKE": "DDOS",
            "INSIDER_ANOMALY": "INSIDER",
            "SUSPICIOUS_LOGIN": "SUSPICIOUS_LOGIN",
        }
        out = []
        for i, ev in enumerate(events):
            rule_key = mapping.get(ev["event_type"])
            if not rule_key:
                continue
            rule = RULES[rule_key]
            meta = ev.get("metadata") or {}
            mean_anom, max_anom = self._ml_confidence([i], vectors)
            evidence = list(meta.get("evidence") or [])
            if not evidence:
                evidence = [ev.get("message") or f"{ev['event_type']} observed on {ev['destination']}"]
            if mean_anom > 0.5:
                evidence.append("Isolation Forest anomaly score %.2f" % mean_anom)
            confidence = 0.84 + min(0.12, mean_anom * 0.18)
            if meta.get("guaranteed"):
                confidence = max(confidence, 0.93)
            out.append(
                {
                    "rule": rule_key,
                    "event_idxs": [i],
                    "source": ev["source"],
                    "destination": ev["destination"],
                    "evidence": evidence,
                    "confidence": min(0.99, confidence),
                    "anomaly": mean_anom,
                    "max_anomaly": max_anom,
                    "count": 1,
                    "event": ev,
                }
            )
        return out

    # ------------------------------------------------------------- threat build
    def build_threat(self, candidate: dict[str, Any], timestamp: float) -> Threat:
        rule = RULES[candidate["rule"]]
        sensitivity = 0
        for n in topology.NODES:
            if n["label"] == candidate["destination"] or n["id"] == candidate["destination"]:
                sensitivity = topology.ASSET_SENSITIVITY[n["id"]]
                break
        severity: Severity = rule["base_severity"]
        if candidate["anomaly"] > 0.75 and severity != Severity.CRITICAL:
            severity = max_severity(severity, Severity.HIGH)
        risk = int(
            min(
                99,
                rule["base_risk"]
                + candidate["anomaly"] * 14
                + sensitivity * 0.08
                + min(candidate["count"], 40) * 0.35,
            )
        )
        affected = candidate["destination"]
        for n in topology.NODES:
            if n["id"] == candidate["destination"]:
                affected = n["label"]
                break
        return Threat(
            id=new_id("THR"),
            threat_type=rule["threat_type"],
            severity=severity,
            risk_score=risk,
            confidence=round(float(candidate["confidence"]), 3),
            anomaly_score=round(float(candidate["anomaly"]), 3),
            affected_asset=affected,
            source=candidate["source"],
            destination=candidate["destination"],
            timestamp=timestamp,
            evidence=candidate["evidence"],
            detector="isolation-forest + rules",
            status="ACTIVE",
        )


DETECTOR = ThreatDetector()
