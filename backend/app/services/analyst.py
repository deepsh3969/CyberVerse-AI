"""AI analyst layer.

Primary path: local deterministic explanation engine built from incident
metadata - always available, no API key required, never fails.
Optional path: an OpenAI-compatible chat completion API when AI_API_KEY is set.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from app.core.config import settings
from app.models.schemas import AIAnalysis, AnalysisSection, Incident, Recommendation
from app.services import topology

SEVERITY_QUESTIONS = {
    "what": "what happened",
    "why": "why is this dangerous",
    "evidence": "what evidence supports this",
    "systems": "which systems are affected",
    "do": "what should we do",
    "timeline": "what is the attack timeline",
    "prevent": "how can we prevent this",
}


def _fmt_time(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _timeline_lines(incident: Incident) -> list[str]:
    lines = []
    for item in sorted(incident.timeline, key=lambda t: t.get("time", 0))[:8]:
        lines.append(f"{_fmt_time(item.get('time', 0))} - {item.get('label', '')}")
    return lines


def _local_analysis(incident: Incident, question: str = "") -> AIAnalysis:
    affected = ", ".join(incident.affected_assets) or "unspecified asset"
    first, last = _fmt_time(incident.first_seen), _fmt_time(incident.last_seen)
    duration = max(0, int(incident.last_seen - incident.first_seen))
    evidence_lines = incident.evidence or ["No structured evidence attached."]
    graph_hint = ""
    path = incident.timeline and next(
        (t.get("detail", "") for t in incident.timeline if t.get("kind") == "graph"), ""
    )
    if path:
        graph_hint = f" Reconstructed attack path: {path}."

    summary = (
        f"{incident.threat_type} activity was detected against {affected} between "
        f"{first} and {last} ({duration}s). The detection engine scored the incident "
        f"{incident.risk_score}/100 with severity {incident.severity.value}."
    )

    sections = [
        AnalysisSection(
            heading="What happened?",
            body=(
                f"A sequence of {len(incident.timeline)} correlated events matched the "
                f"{incident.threat_type} behaviour profile. Source {incident.source or 'unknown'} "
                f"reached {affected} through {incident.destination or 'the internal network'} and "
                f"triggered the anomaly model.{path_hint(path)}"
            ),
        ),
        AnalysisSection(
            heading="Why is this dangerous?",
            body=_danger_body(incident),
        ),
        AnalysisSection(
            heading="Evidence",
            body="\n".join(f"- {e}" for e in evidence_lines),
        ),
        AnalysisSection(
            heading="Affected systems",
            body=_systems_body(incident),
        ),
        AnalysisSection(
            heading="Attack timeline",
            body="\n".join(_timeline_lines(incident)) or f"First seen {first}, last seen {last}.",
        ),
        AnalysisSection(
            heading="How can we prevent recurrence?",
            body=_prevention_body(incident),
        ),
    ]

    answer = _answer_question(incident, question)
    if answer:
        sections.insert(0, AnalysisSection(heading="Analyst answer", body=answer))

    return AIAnalysis(
        incident_id=incident.id,
        provider="local-analysis-engine",
        summary=summary,
        sections=sections,
        recommendations=incident.recommendations
        or [
            Recommendation(title="Review detection coverage",
                           detail="Confirm the relevant log sources are onboarded for this asset class.",
                           priority="MEDIUM")
        ],
        generated_at=time.time(),
    )


def path_hint(path: str) -> str:
    return f" Reconstructed attack path: {path}." if path else ""


def _danger_body(incident: Incident) -> str:
    reasons = {
        "Brute Force": "Successful authentication after repeated failures means an attacker may hold valid credentials. From there they can read or modify data reachable by that identity.",
        "Port Scan": "Reconnaissance is the preparation stage of an attack. Enumerated services are then probed for known vulnerabilities before exploitation.",
        "Suspicious Login": "A valid session from an unknown device or region can indicate credential theft. Every action taken inside that session inherits the victim's privileges.",
        "Privilege Escalation": "Elevated privileges turn a limited compromise into full host control, enabling persistence and lateral movement.",
        "Data Exfiltration": "Bulk egress of protected records is a direct confidentiality breach with regulatory and reputational consequences.",
        "Malware Activity": "A packed payload in a served directory can execute attacker code, establish persistence and pivot to adjacent systems.",
        "DDoS Traffic Spike": "Sustained saturation degrades or denies service to legitimate users and can mask a quieter intrusion attempt.",
        "Insider Threat": "Legitimate credentials bypass perimeter controls, so unusual volume or timing by an insider is often the only remaining signal.",
    }
    base = reasons.get(
        incident.threat_type,
        "Anomalous activity that deviates from the established baseline of this asset.",
    )
    extra = (
        f" Current risk score of {incident.risk_score}/100 reflects both the anomaly strength "
        f"and the sensitivity of {', '.join(incident.affected_assets) or 'the affected asset'}."
    )
    return base + extra


def _systems_body(incident: Incident) -> str:
    lines = []
    for asset in incident.affected_assets or ["Unknown"]:
        node = next((n for n in topology.NODES if n["label"] == asset or n["id"] == asset), None)
        if node:
            lines.append(
                f"- {node['label']} ({node['zone']} zone, {node['ip']}, sensitivity "
                f"{topology.ASSET_SENSITIVITY[node['id']]}/100): {node['description']}"
            )
        else:
            lines.append(f"- {asset}")
    neighbours = [
        topology.label_of(e["target"]) if e["source"] in [n["id"] for n in topology.NODES] else topology.label_of(e["source"])
        for e in _edges_touching(incident)
    ]
    if neighbours:
        lines.append("- Adjacent assets to monitor: " + ", ".join(sorted(set(neighbours))))
    return "\n".join(lines) or "- No mapped assets."


def _edges_touching(incident: Incident):
    from app.services import topology as topo

    ids = set()
    for asset in incident.affected_assets:
        for n in topo.NODES:
            if n["label"] == asset or n["id"] == asset:
                ids.add(n["id"])
    return [e for e in topo.EDGES if e["source"] in ids or e["target"] in ids]


def _prevention_body(incident: Incident) -> str:
    tips = {
        "Brute Force": "Phishing-resistant MFA, exponential backoff, and blocking after N failures.",
        "Port Scan": "Perimeter rate limiting, published-port review, and IDS scan signatures.",
        "Suspicious Login": "Impossible-travel detection, new-device challenge, and session binding.",
        "Privilege Escalation": "Just-in-time privileges, sudo approval workflow, and integrity monitoring.",
        "Data Exfiltration": "Egress allow-listing, DLP inspection, and bulk-export approval.",
        "Malware Activity": "Application allow-listing, write protection on served directories, and egress DNS filtering.",
        "DDoS Traffic Spike": "Edge scrubbing, per-IP quotas, and warm autoscaling.",
        "Insider Threat": "Least-privilege grants, query-volume baselines, and periodic access reviews.",
    }
    return tips.get(
        incident.threat_type,
        "Baseline behavioural monitoring with alerting on deviation and periodic control reviews.",
    )


def _answer_question(incident: Incident, question: str) -> str:
    q = question.lower().strip()
    if not q:
        return ""
    if any(k in q for k in ("what happened", "what's happened", "summar", "explain", "happened")):
        return (
            f"{incident.threat_type} detected against {', '.join(incident.affected_assets)} "
            f"from source {incident.source}. Risk {incident.risk_score}/100, severity "
            f"{incident.severity.value}, status {incident.status.value}."
        )
    if "why" in q or "danger" in q or "risk" in q:
        return _danger_body(incident)
    if "evidence" in q or "proof" in q or "indicator" in q:
        return "\n".join(f"- {e}" for e in (incident.evidence or ["None recorded."]))
    if any(k in q for k in ("system", "asset", "affected", "host", "target")):
        return _systems_body(incident)
    if any(k in q for k in ("do ", "action", "recommend", "respond", "should we", "mitigat")):
        return "\n".join(
            f"{i + 1}. {r.title} - {r.detail}" for i, r in enumerate(incident.recommendations)
        ) or "No recommendations generated."
    if "timeline" in q or "sequence" in q or "when" in q:
        return "\n".join(_timeline_lines(incident)) or "No timeline recorded."
    if any(k in q for k in ("prevent", "avoid", "recurrence", "hardening")):
        return _prevention_body(incident)
    return (
        f"Regarding '{question}': {incident.threat_type} incident {incident.id} is "
        f"{incident.status.value} with risk {incident.risk_score}/100 affecting "
        f"{', '.join(incident.affected_assets)}."
    )


def _llm_analysis(incident: Incident, question: str) -> Optional[AIAnalysis]:
    if not settings.llm_enabled:
        return None
    prompt = (
        "You are a senior SOC analyst. Explain this incident for a security team.\n"
        f"Incident JSON:\n{incident.model_dump_json(indent=2)}\n\n"
        f"Analyst question: {question or 'Provide a full analysis.'}\n\n"
        "Respond with JSON: {\"summary\": str, \"sections\": [{\"heading\": str, \"body\": str}], "
        "\"recommendations\": [{\"title\": str, \"detail\": str, \"priority\": str}]}"
    )
    try:
        import httpx

        resp = httpx.post(
            f"{settings.ai_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.ai_api_key}"},
            json={
                "model": settings.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return AIAnalysis(
            incident_id=incident.id,
            provider=f"{settings.ai_provider}:{settings.ai_model}",
            summary=data.get("summary", ""),
            sections=[AnalysisSection(**s) for s in data.get("sections", [])],
            recommendations=[Recommendation(**r) for r in data.get("recommendations", [])],
            generated_at=time.time(),
        )
    except Exception:
        return None


def analyze(incident: Incident, question: str = "") -> AIAnalysis:
    return _llm_analysis(incident, question) or _local_analysis(incident, question)


def quick_assessment(threat_type: str, asset: str, score: int) -> str:
    return (
        f"{threat_type} against {asset} scored {score}/100. "
        f"{'Immediate containment recommended.' if score >= 80 else 'Monitor and validate.'}"
    )
