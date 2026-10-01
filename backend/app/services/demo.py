"""Scripted 2-3 minute hackathon demo.

Runs in a background thread, advancing a numbered timeline that the frontend
polls. Every action is simulated inside the sandbox.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from app.services.analyst import analyze
from app.services.engine import ENGINE
from app.services.store import STORE

STEPS = [
    ("Normal network baseline", "All assets healthy, telemetry flowing at expected rates."),
    ("Suspicious traffic begins", "Reconnaissance probes arrive at the perimeter."),
    ("Multiple failed logins", "Credential guessing escalates against the identity provider."),
    ("AI detects anomaly", "Isolation Forest and the rule engine correlate the sequence."),
    ("Threat visible in 3D network", "Affected nodes change state on the cyber map."),
    ("Incident generated", "Case opened with severity, risk score and evidence."),
    ("Attack graph reconstructed", "Lateral path from attacker to crown-jewel data."),
    ("AI analyst explanation", "Structured analysis of what, why, evidence and impact."),
    ("Recommended actions", "Contextual defensive playbook attached to the incident."),
    ("Containment requested", "Analyst triggers simulated containment."),
    ("Threat contained", "Session terminated, path blocked, endpoint isolated."),
    ("Recovery", "Assets return to a monitored, secure state."),
]


class DemoRunner:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.state: dict[str, Any] = {
            "state": "idle",
            "step": -1,
            "label": "",
            "detail": "",
            "started_at": None,
            "incident_id": None,
            "scenario": "brute-force",
            "steps": [{"index": i, "label": s[0], "detail": s[1]} for i, s in enumerate(STEPS)],
        }

    # ------------------------------------------------------------------ control
    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            data = dict(self.state)
            data["steps"] = list(self.state["steps"])
            return data

    def start(self) -> dict[str, Any]:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return self.snapshot()
            self.stop_event.clear()
            self.state.update(
                {
                    "state": "running",
                    "step": 0,
                    "label": STEPS[0][0],
                    "detail": STEPS[0][1],
                    "started_at": time.time(),
                    "incident_id": None,
                }
            )
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            return self.snapshot()

    def reset(self) -> dict[str, Any]:
        with self.lock:
            if self.thread and self.thread.is_alive():
                # Ask the runner to exit, then wait briefly for it to do so.
                self.stop_event.set()
                self.thread.join(timeout=3.0)
            if self.thread and self.thread.is_alive():
                return {"state": "busy", "message": "Demo still running"}
            STORE.full_reset()
            ENGINE.seed()
            STORE.demo = {"state": "idle", "step": -1, "started_at": None}
            self.state.update(
                {
                    "state": "idle",
                    "step": -1,
                    "label": "",
                    "detail": "",
                    "started_at": None,
                    "incident_id": None,
                }
            )
            return self.snapshot()

    def stop(self) -> dict[str, Any]:
        with self.lock:
            self.stop_event.set()
            self.state["state"] = "aborted"
            self.state["label"] = "Demo stopped"
            self.state["detail"] = "Operator stopped the scripted sequence."
            return self.snapshot()

    # ---------------------------------------------------------------- execution
    def _set(self, step: int, **extra: Any) -> None:
        with self.lock:
            self.state.update(
                {
                    "step": step,
                    "label": STEPS[step][0],
                    "detail": STEPS[step][1],
                    **extra,
                }
            )

    def _pause(self, seconds: float) -> bool:
        """Wait ``seconds``; returns True when a stop/reset was requested."""
        return self.stop_event.wait(seconds)

    def _run(self) -> None:
        try:
            if self._pause(1.6):
                return
            self._set(1)

            scan = ENGINE.run_scenario("port-scan", intensity="low")
            if self._pause(2.4):
                return

            self._set(2)
            result = ENGINE.run_scenario("brute-force", intensity="normal")
            if self._pause(2.2):
                return

            incident = result.incident
            threats = result.threats
            if incident is None:
                self._set(3, state="failed", detail="Detection did not raise an incident.")
                return

            self._set(3)
            if self._pause(2.0):
                return
            self._set(4)
            if self._pause(2.0):
                return
            self._set(5, incident_id=incident.id)
            if self._pause(2.0):
                return
            self._set(6, incident_id=incident.id)
            if self._pause(2.0):
                return

            analysis = analyze(incident, "What happened and why is it dangerous?")
            incident.analysis = analysis
            STORE.add_incident(incident)
            self._set(7, incident_id=incident.id)
            if self._pause(2.0):
                return
            self._set(8, incident_id=incident.id)
            if self._pause(2.0):
                return
            self._set(9, incident_id=incident.id)

            # wait for the operator to press CONTAIN THREAT
            deadline = time.time() + 90
            while time.time() < deadline:
                current = STORE.get_incident(incident.id)
                if current and current.status.value in ("CONTAINED", "RESOLVED"):
                    break
                if self._pause(0.7):
                    return
            else:
                with self.lock:
                    self.state["state"] = "timeout"
                    self.state["label"] = "Waiting for containment"
                    self.state["detail"] = "Open the incident and press CONTAIN THREAT to finish the demo."
                return

            self._set(10, incident_id=incident.id)
            if self._pause(1.8):
                return
            self._set(11, incident_id=incident.id)
            if self._pause(1.4):
                return
            with self.lock:
                self.state["state"] = "complete"
                self.state["label"] = "Demo complete"
                self.state["detail"] = "Network returned to a secure, monitored state."
                self.state["finished_at"] = time.time()
        except Exception as exc:  # pragma: no cover
            with self.lock:
                self.state["state"] = "failed"
                self.state["label"] = "Demo error"
                self.state["detail"] = f"{type(exc).__name__}: {exc}"


DEMO = DemoRunner()
