"""Application engine: wires simulation, detection, incidents, graphs, reporting."""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any, Optional

from app.ml.detector import DETECTOR, RULES
from app.ml.features import FeatureBuilder
from app.models.schemas import (
    AIAnalysis,
    AttackGraph,
    ContainmentResult,
    Dashboard,
    Event,
    GraphEdge,
    GraphNode,
    Incident,
    IncidentStatus,
    Network,
    NetworkEdge,
    NetworkNode,
    Recommendation,
    Severity,
    SimulationResult,
    Threat,
    ThreatLevel,
)
from app.services import topology
from app.services.store import STORE, new_id
from app.simulator.scenarios import build_scenario, seed_events

SEVERITY_RANK = {s: i for i, s in enumerate([Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL])}


# --------------------------------------------------------------- recommendations
def recommendations_for(threat_type: str) -> list[Recommendation]:
    common = [
        Recommendation(title="Increase monitoring on related assets",
                       detail="Raise log verbosity and stream correlated telemetry to the SOC for 24 hours.",
                       priority="MEDIUM"),
    ]
    specific: dict[str, list[Recommendation]] = {
        "Brute Force": [
            Recommendation(title="Temporarily isolate the affected account", detail="Disable interactive sign-in for the targeted identity and force a credential reset (simulated).", priority="HIGH"),
            Recommendation(title="Require MFA", detail="Step up the identity to phishing-resistant MFA before access is restored.", priority="HIGH"),
            Recommendation(title="Block the suspicious source", detail="Add the offending address to the edge deny list with a 24 hour TTL.", priority="MEDIUM"),
            Recommendation(title="Review authentication logs", detail="Correlate sign-in attempts across VPN, web and API tiers for lateral movement.", priority="MEDIUM"),
        ],
        "Port Scan": [
            Recommendation(title="Enable automatic rate limiting", detail="Throttle SYN packets per source at the perimeter firewall (simulated).", priority="MEDIUM"),
            Recommendation(title="Close unused services", detail="Confirm only required ports are published in the DMZ.", priority="MEDIUM"),
            Recommendation(title="Watch for follow-up exploitation", detail="Monitor the scanned assets for exploit attempts in the next hour.", priority="HIGH"),
        ],
        "Suspicious Login": [
            Recommendation(title="Force step-up authentication", detail="Challenge the active session with MFA or terminate it (simulated).", priority="HIGH"),
            Recommendation(title="Validate the user", detail="Out-of-band confirmation with the account owner before restoring access.", priority="HIGH"),
            Recommendation(title="Review session activity", detail="Inspect API calls made since the anomalous sign-in.", priority="MEDIUM"),
        ],
        "Privilege Escalation": [
            Recommendation(title="Suspend the elevated identity", detail="Revoke tokens and disable the service account pending review (simulated).", priority="CRITICAL"),
            Recommendation(title="Audit sudo and role bindings", detail="Diff standing privileges against the approved baseline.", priority="HIGH"),
            Recommendation(title="Remove persistence artifacts", detail="Quarantine the newly written auto-start unit (simulated).", priority="HIGH"),
        ],
        "Data Exfiltration": [
            Recommendation(title="Block the egress destination", detail="Deny the external host at the perimeter and sinkhole DNS (simulated).", priority="CRITICAL"),
            Recommendation(title="Rotate exposed credentials", detail="Invalidate sessions and secrets reachable by the export path.", priority="CRITICAL"),
            Recommendation(title="Preserve forensic evidence", detail="Snapshot affected hosts and export flow records before remediation.", priority="HIGH"),
            Recommendation(title="Notify the data owner", detail="Flag affected record classes for compliance review.", priority="MEDIUM"),
        ],
        "Malware Activity": [
            Recommendation(title="Isolate the endpoint", detail="Move the host to a quarantine VLAN (simulated containment).", priority="CRITICAL"),
            Recommendation(title="Quarantine the file", detail="Remove or neutralize the dropped artifact and block its hash.", priority="CRITICAL"),
            Recommendation(title="Run a full endpoint scan", detail="Schedule an offline scan of the affected workload.", priority="HIGH"),
        ],
        "DDoS Traffic Spike": [
            Recommendation(title="Activate traffic scrubbing", detail="Route inbound traffic through the cleaning service (simulated).", priority="HIGH"),
            Recommendation(title="Lower the per-IP request cap", detail="Apply aggressive rate limits at the CDN and edge.", priority="HIGH"),
            Recommendation(title="Scale out the web tier", detail="Add warm capacity to absorb the request burst (simulated).", priority="MEDIUM"),
        ],
        "Insider Threat": [
            Recommendation(title="Restrict the account", detail="Apply session limits and block bulk export endpoints (simulated).", priority="HIGH"),
            Recommendation(title="Review data access history", detail="Reconstruct 30 days of access for the identity.", priority="HIGH"),
            Recommendation(title="Enforce least privilege", detail="Reduce table-level grants to the minimum required for the role.", priority="MEDIUM"),
        ],
    }
    return specific.get(threat_type, []) + common


# --------------------------------------------------------------------- engine
class Engine:
    # ------------------------------------------------------------- simulation
    def run_scenario(self, scenario_key: str, intensity: str = "normal", target: str = "") -> SimulationResult:
        output = build_scenario(scenario_key, intensity, target)
        events = self.ingest(output.events)
        threats = self.detect_stored()
        if not threats:
            threats = self._fallback_threat(output)
        incident: Optional[Incident] = None
        graph: Optional[AttackGraph] = None
        if threats:
            primary = max(threats, key=lambda t: t.risk_score)
            incident = self._upsert_incident(primary, output.events)
            graph = self.build_attack_graph(incident, output.attack_path, primary)
        STORE.record_risk()
        return SimulationResult(
            scenario=output.name,
            events=events,
            threats=threats,
            incident=incident,
            attack_graph=graph,
            message=output.summary,
        )

    def ingest(self, raw_events: list[dict]) -> list[Event]:
        builder = FeatureBuilder()
        stored: list[Event] = []
        vectors = []
        contexts = []
        ordered = sorted(raw_events, key=lambda e: e["timestamp"])
        for raw in ordered:
            ev = dict(raw)
            vectors.append(builder.vector(ev))
            contexts.append(builder.context(ev))
            record = STORE.add_event(ev)
            stored.append(Event(**record))
        self._last_vectors = vectors
        self._last_contexts = contexts
        self._last_events = ordered
        return stored

    def detect_stored(self) -> list[Threat]:
        """Run detection over the most recently ingested batch."""
        events = getattr(self, "_last_events", [])
        vectors = getattr(self, "_last_vectors", [])
        contexts = getattr(self, "_last_contexts", [])
        candidates = DETECTOR.detect(events, vectors, contexts)
        threats: list[Threat] = []
        seen_rules: set[str] = set()
        for cand in candidates:
            if cand["rule"] in seen_rules:
                continue
            seen_rules.add(cand["rule"])
            ts = events[cand["event_idxs"][-1]]["timestamp"]
            threat = DETECTOR.build_threat(cand, ts)
            STORE.add_threat(threat)
            threats.append(threat)
        return threats

    def _threats_for(self, events: list[Event]) -> list[Threat]:
        return self.detect_stored()

    def _fallback_threat(self, output) -> list[Threat]:
        """Guarantee the demo never stalls: synthesise a threat from scenario metadata."""
        from app.simulator.scenarios import SCENARIO_META

        anchor = None
        for ev in output.events:
            meta = ev.get("metadata") or {}
            if meta.get("guaranteed"):
                anchor = ev
        if anchor is None and output.events:
            anchor = output.events[-1]
        if anchor is None:
            return []
        meta_key = output.key
        info = next((m for m in SCENARIO_META if m["key"] == meta_key), None)
        rule = {
            "port-scan": "PORT_SCAN",
            "brute-force": "BRUTE_FORCE",
            "suspicious-login": "SUSPICIOUS_LOGIN",
            "privilege-escalation": "PRIVILEGE_ESCALATION",
            "data-exfiltration": "DATA_EXFILTRATION",
            "malware": "MALWARE",
            "ddos": "DDOS",
            "insider-anomaly": "INSIDER",
        }.get(meta_key, "PORT_SCAN")
        from app.ml.detector import RULES

        r = RULES[rule]
        meta = anchor.get("metadata") or {}
        evidence = list(meta.get("evidence") or [anchor["message"]])
        affected = anchor["destination"]
        for n in topology.NODES:
            if n["id"] == anchor["destination"]:
                affected = n["label"]
                break
        threat = Threat(
            id=new_id("THR"),
            threat_type=r["threat_type"],
            severity=r["base_severity"],
            risk_score=r["base_risk"],
            confidence=0.9,
            anomaly_score=0.7,
            affected_asset=affected,
            source=anchor["source"],
            destination=anchor["destination"],
            timestamp=anchor["timestamp"],
            evidence=evidence,
            detector="rules (fallback)",
            status="ACTIVE",
        )
        STORE.add_threat(threat)
        return [threat]

    # -------------------------------------------------------------- incidents
    def _upsert_incident(self, threat: Threat, events: list[dict]) -> Incident:
        now = time.time()
        existing = None
        for inc in STORE.list_incidents():
            if (
                inc.threat_type == threat.threat_type
                and inc.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)
                and now - inc.last_seen < 600
            ):
                existing = inc
                break
        timeline_events = [
            {
                "time": e["timestamp"],
                "kind": e["event_type"],
                "label": e["message"],
                "detail": f"{e['source']} → {e['destination']}",
            }
            for e in events
        ]
        if existing:
            existing.last_seen = max(existing.last_seen, threat.timestamp)
            existing.risk_score = max(existing.risk_score, threat.risk_score)
            existing.severity = threat.severity if SEVERITY_RANK[threat.severity] > SEVERITY_RANK[existing.severity] else existing.severity
            for ev in threat.evidence:
                if ev not in existing.evidence:
                    existing.evidence.append(ev)
            existing.threat_ids.append(threat.id)
            existing.timeline.extend(timeline_events)
            if threat.affected_asset not in existing.affected_assets:
                existing.affected_assets.append(threat.affected_asset)
            STORE.add_incident(existing)
            return existing

        incident = Incident(
            id=new_id("INC"),
            threat_type=threat.threat_type,
            severity=threat.severity,
            risk_score=threat.risk_score,
            status=IncidentStatus.OPEN,
            first_seen=min([e["timestamp"] for e in events], default=threat.timestamp),
            last_seen=max([e["timestamp"] for e in events], default=threat.timestamp),
            affected_assets=[threat.affected_asset],
            source=threat.source,
            destination=threat.destination,
            evidence=list(threat.evidence),
            timeline=timeline_events,
            threat_ids=[threat.id],
            recommendations=recommendations_for(threat.threat_type),
        )
        incident.timeline.append(
            {
                "time": now,
                "kind": "detect",
                "label": "AI detection engine raised a threat",
                "detail": f"{threat.threat_type} · confidence {threat.confidence:.2f} · risk {threat.risk_score}",
            }
        )
        STORE.add_incident(incident)
        return incident

    # ------------------------------------------------------------ attack graph
    def build_attack_graph(self, incident: Incident, path: list[str], threat: Threat) -> AttackGraph:
        path = path or ["attacker", "internet", "firewall", "web"]
        pseudo = {
            "attacker": ("External Attacker", "attacker", "Untrusted actor originating the campaign."),
            "botnet": ("Botnet Cluster", "attacker", "Distributed hosts used to flood the target."),
            "insider": ("Internal User", "attacker", "Authenticated insider acting outside normal behavior."),
            "account": ("Compromised Account", "account", "Identity credentials abused during the attack."),
        }
        nodes: list[GraphNode] = []
        now = time.time()
        destructive = SEVERITY_RANK[threat.severity] >= SEVERITY_RANK[Severity.HIGH]
        for idx, pid in enumerate(path):
            if pid in pseudo:
                label, kind, detail = pseudo[pid]
                status = "compromised" if kind == "account" and destructive else "monitoring"
                nodes.append(GraphNode(id=pid, label=label, kind=kind, status=status,
                                       risk=90 if status == "compromised" else 70,
                                       compromised_at=now if status == "compromised" else None,
                                       detail=detail))
                continue
            node = topology.get_node(pid)
            if not node:
                continue
            step_status = "compromised" if (idx >= 2 and destructive) else ("monitoring" if idx < 2 else "warning")
            STORE.set_node_status(pid, "compromised" if step_status == "compromised" else "warning")
            nodes.append(
                GraphNode(
                    id=pid,
                    label=node["label"],
                    kind="asset",
                    status=step_status,  # type: ignore[arg-type]
                    risk=STORE.node_risk.get(pid, 40),
                    compromised_at=now if step_status == "compromised" else None,
                    detail=node["description"],
                )
            )
        edges = [
            GraphEdge(source=path[i], target=path[i + 1], label="traversal", active=True,
                      severity=threat.severity)
            for i in range(len(path) - 1)
        ]
        graph = AttackGraph(
            incident_id=incident.id,
            nodes=nodes,
            edges=edges,
            path_labels=[n.label for n in nodes],
            created_at=now,
        )
        STORE.set_graph(incident.id, graph.model_dump(mode="json"))
        incident.timeline.append(
            {
                "time": now,
                "kind": "graph",
                "label": "Attack path reconstructed",
                "detail": " → ".join(graph.path_labels),
            }
        )
        STORE.add_incident(incident)
        return graph

    # ------------------------------------------------------------- containment
    def contain(self, incident_id: str, actor: str = "analyst") -> Optional[ContainmentResult]:
        incident = STORE.get_incident(incident_id)
        if not incident:
            return None
        now = time.time()
        graph = STORE.get_graph(incident_id)
        actions = [
            "Endpoint isolated (simulated)",
            "Suspicious session terminated (simulated)",
            "Threat path blocked at the firewall (simulated)",
            "Monitoring increased on related assets (simulated)",
        ]
        for asset in incident.affected_assets:
            for n in topology.NODES:
                if n["label"] == asset or n["id"] == asset:
                    STORE.set_node_status(n["id"], "contained", risk=max(10, STORE.node_risk.get(n["id"], 40) - 35))
                    break
        if graph:
            for node in graph.get("nodes", []):
                kind = node.get("kind")
                if kind == "asset":
                    topo = topology.get_node(node["id"]) or {}
                    if topo.get("zone") != "external":
                        STORE.set_node_status(
                            node["id"], "contained",
                            risk=max(10, STORE.node_risk.get(node["id"], 40) - 35),
                        )
                    node["status"] = "contained"
                elif kind == "account":
                    node["status"] = "contained"
            for edge in graph.get("edges", []):
                edge["active"] = False
                edge["label"] = "blocked"
            STORE.set_graph(incident_id, graph)
        for threat_id in incident.threat_ids:
            threat = STORE.threats.get(threat_id)
            if threat:
                threat.status = "CONTAINED"
        STORE.threats_blocked += max(1, len(incident.threat_ids))
        incident.status = IncidentStatus.CONTAINED
        incident.containment = {
            "at": now,
            "by": actor,
            "actions": actions,
            "mode": "simulation",
            "note": "All containment actions are simulated inside the CyberVerse sandbox.",
        }
        incident.timeline.append(
            {
                "time": now,
                "kind": "contain",
                "label": "THREAT CONTAINED",
                "detail": " · ".join(actions),
            }
        )
        STORE.add_incident(incident)
        STORE.record_risk()
        return ContainmentResult(incident=incident, actions=actions)

    # ---------------------------------------------------------------- network
    def network(self) -> Network:
        nodes = []
        for n in topology.NODES:
            nodes.append(
                NetworkNode(
                    id=n["id"],
                    label=n["label"],
                    type=n["type"],
                    status=STORE.node_status.get(n["id"], "healthy"),  # type: ignore[arg-type]
                    risk=STORE.node_risk.get(n["id"], 10),
                    ip=n["ip"],
                    zone=n["zone"],
                    description=n["description"],
                    position=tuple(n["position"]),  # type: ignore[arg-type]
                )
            )
        edges = [
            NetworkEdge(
                source=e["source"],
                target=e["target"],
                label=e["label"],
                status=self._edge_status(e),
            )
            for e in topology.EDGES
        ]
        return Network(nodes=nodes, edges=edges, updated_at=time.time())

    @staticmethod
    def _edge_status(edge: dict) -> str:
        s1 = STORE.node_status.get(edge["source"], "healthy")
        s2 = STORE.node_status.get(edge["target"], "healthy")
        if s1 == "compromised" or s2 == "compromised":
            return "attack"
        if s1 == "warning" or s2 == "warning":
            return "warning"
        if s1 == "contained" or s2 == "contained":
            return "contained"
        return "idle"

    # --------------------------------------------------------------- dashboard
    def dashboard(self) -> Dashboard:
        now = time.time()
        events = list(STORE.events)
        threats = STORE.list_threats(200)
        incidents = STORE.list_incidents()
        active = [i for i in incidents if i.status in (IncidentStatus.OPEN, IncidentStatus.INVESTIGATING)]
        score = STORE.security_score()

        # threats over time (5 minute buckets, last 60 min)
        bucket = 300.0
        start = now - 3600
        buckets = {}
        for b in range(12):
            t0 = start + b * bucket
            buckets[round(t0)] = {"benign": 0, "threat": 0}
        threat_times = [t.timestamp for t in threats]
        for ev in events:
            if ev["timestamp"] < start:
                continue
            key = round(start + int((ev["timestamp"] - start) // bucket) * bucket)
            if key in buckets:
                buckets[key]["threat" if ev["severity"] in ("HIGH", "CRITICAL") else "benign"] += 1
        events_over_time = [
            {"time": k, "benign": v["benign"], "threat": v["threat"]} for k, v in sorted(buckets.items())
        ]

        cat_counter: dict[str, int] = defaultdict(int)
        for t in threats:
            cat_counter[t.threat_type] += 1
        threat_categories = [{"name": k, "value": v} for k, v in sorted(cat_counter.items(), key=lambda x: -x[1])]

        risk_history = STORE.risk_history[-60:] or [{"time": now, "score": score}]

        volume: dict[int, int] = defaultdict(int)
        for ev in events:
            if ev["timestamp"] >= now - 900:
                volume[int(ev["timestamp"] // 60)] += 1
        event_volume = [{"time": k * 60, "count": v} for k, v in sorted(volume.items())]

        sev_counter: dict[str, int] = defaultdict(int)
        for t in threats:
            sev_counter[t.severity.value] += 1
        severity_distribution = [
            {"severity": s, "count": sev_counter.get(s, 0)}
            for s in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        ]

        top_assets = sorted(
            [
                {
                    "asset": topology.label_of(nid),
                    "risk": risk,
                    "status": STORE.node_status.get(nid, "healthy"),
                }
                for nid, risk in STORE.node_risk.items()
            ],
            key=lambda a: -a["risk"],
        )[:5]

        level = self._threat_level(score, active, threats)
        return Dashboard(
            security_score=score,
            threat_level=level,
            active_incidents=len(active),
            protected_assets=len(topology.NODES),
            events_analyzed=STORE.events_analyzed,
            threats_blocked=STORE.threats_blocked,
            events_over_time=events_over_time,
            threat_categories=threat_categories,
            risk_history=[{"time": int(p["time"]), "score": p["score"]} for p in risk_history],
            event_volume=event_volume,
            severity_distribution=severity_distribution,
            recent_threats=threats[:6],
            top_assets=top_assets,
        )

    @staticmethod
    def _threat_level(score: int, active: list[Incident], threats: list[Threat]) -> ThreatLevel:
        max_risk = max([i.risk_score for i in active], default=0)
        if max_risk >= 90 or score < 50:
            return ThreatLevel(level="CRITICAL", score=max_risk or 100 - score, color="#ff3b5c")
        if max_risk >= 78 or score < 70:
            return ThreatLevel(level="HIGH", score=max_risk or 100 - score, color="#ff8a3d")
        if max_risk >= 60 or score < 85:
            return ThreatLevel(level="ELEVATED", score=max_risk or 100 - score, color="#f5c518")
        return ThreatLevel(level="LOW", score=max(4, 100 - score), color="#2fd98a")

    # ---------------------------------------------------------------- seeding
    def seed(self) -> None:
        if STORE.seeded:
            return
        events = seed_events(260)
        builder = FeatureBuilder()
        for ev in events:
            STORE.add_event(dict(ev))
            builder.vector(ev)
        DETECTOR.load_or_train(events)
        # one pre-existing, resolved incident so the console is never empty
        ts = time.time() - 1400
        threat = Threat(
            id=new_id("THR"),
            threat_type="Port Scan",
            severity=Severity.MEDIUM,
            risk_score=57,
            confidence=0.87,
            anomaly_score=0.61,
            affected_asset="Perimeter Firewall",
            source="198.51.100.90",
            destination="firewall",
            timestamp=ts + 40,
            evidence=[
                "11 distinct ports probed from 198.51.100.90",
                "Sequential service enumeration against Perimeter Firewall",
                "Anomaly score 0.61 on scan bursts",
            ],
            status="CONTAINED",
        )
        STORE.add_threat(threat)
        incident = Incident(
            id=new_id("INC"),
            threat_type="Port Scan",
            severity=Severity.MEDIUM,
            risk_score=57,
            status=IncidentStatus.RESOLVED,
            first_seen=ts,
            last_seen=ts + 60,
            affected_assets=["Perimeter Firewall"],
            source="198.51.100.90",
            destination="firewall",
            evidence=list(threat.evidence),
            threat_ids=[threat.id],
            recommendations=recommendations_for("Port Scan"),
            timeline=[
                {"time": ts, "kind": "NETWORK_PORT_SCAN", "label": "Sequential SYN probes detected",
                 "detail": "198.51.100.90 → Perimeter Firewall"},
                {"time": ts + 40, "kind": "detect", "label": "AI detection engine raised a threat",
                 "detail": "Port Scan · confidence 0.87 · risk 57"},
                {"time": ts + 220, "kind": "contain", "label": "THREAT CONTAINED",
                 "detail": "Rate limit applied and source blocked (simulated)"},
                {"time": ts + 900, "kind": "status", "label": "Status changed to RESOLVED",
                 "detail": "Analyst verification complete"},
            ],
            containment={
                "at": ts + 220,
                "by": "analyst",
                "actions": ["Source address blocked (simulated)", "Rate limit tightened (simulated)"],
                "mode": "simulation",
            },
        )
        STORE.add_incident(incident)

        # one open, investigable case so every console has live content on first load
        ts2 = time.time() - 640
        threat2 = Threat(
            id=new_id("THR"),
            threat_type="Suspicious Login",
            severity=Severity.MEDIUM,
            risk_score=66,
            confidence=0.89,
            anomaly_score=0.68,
            affected_asset="Authentication Server",
            source="203.0.113.77",
            destination="auth",
            timestamp=ts2 + 90,
            evidence=[
                "Sign-in from a device never previously observed",
                "Geographic hop inconsistent with prior session history",
                "46 profile API calls within 3 minutes of the login",
            ],
            status="ACTIVE",
        )
        STORE.add_threat(threat2)
        open_incident = Incident(
            id=new_id("INC"),
            threat_type="Suspicious Login",
            severity=Severity.MEDIUM,
            risk_score=66,
            status=IncidentStatus.INVESTIGATING,
            first_seen=ts2,
            last_seen=ts2 + 210,
            affected_assets=["Authentication Server", "Remote Access Gateway"],
            source="203.0.113.77",
            destination="auth",
            evidence=list(threat2.evidence),
            threat_ids=[threat2.id],
            recommendations=recommendations_for("Suspicious Login"),
            timeline=[
                {"time": ts2, "kind": "SUSPICIOUS_LOGIN", "label": "Login from unseen device and region",
                 "detail": "203.0.113.77 → Remote Access Gateway"},
                {"time": ts2 + 90, "kind": "detect", "label": "AI detection engine raised a threat",
                 "detail": "Suspicious Login · confidence 0.89 · risk 66"},
                {"time": ts2 + 210, "kind": "API_CALL", "label": "Rapid enumeration of user profile endpoints",
                 "detail": "203.0.113.77 → API Server"},
            ],
        )
        STORE.add_incident(open_incident)
        from app.services.analyst import analyze as _analyze

        open_incident.analysis = _analyze(open_incident)
        STORE.add_incident(open_incident)
        self.build_attack_graph(
            open_incident, ["attacker", "internet", "vpn", "auth", "account"], threat2
        )
        for nid in ("vpn", "auth"):
            STORE.set_node_status(nid, "warning")
            STORE.node_risk[nid] = min(STORE.node_risk.get(nid, 40), 48)
        STORE.node_risk["firewall"] = min(STORE.node_risk.get("firewall", 40), 42)

        STORE.threats_blocked = 47
        for p in range(30):
            STORE.risk_history.append(
                {"time": time.time() - (30 - p) * 180, "score": 92 - (p % 5)}
            )
        STORE.seeded = True


ENGINE = Engine()
