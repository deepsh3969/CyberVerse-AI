"""All HTTP routes for the CyberVerse AI backend."""
from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import require_read, require_role
from app.api.ratelimit import client_ip, rate_limit
from app.core.config import settings
from app.ml.detector import DETECTOR
from app.models.schemas import (
    AIAnalysis,
    AnalyzeRequest,
    AnalyzeResponse,
    ContainmentResult,
    Dashboard,
    Event,
    HealthResponse,
    Incident,
    IncidentStatus,
    Network,
    SimulationRequest,
    SimulationResult,
    Threat,
)
from app.services import topology
from app.services.analyst import analyze
from app.services.audit import audit
from app.services.demo import DEMO
from app.services.engine import ENGINE
from app.services.store import STORE
from app.simulator.scenarios import SCENARIO_META

router = APIRouter()

STARTED_AT = time.time()
VERSION = "1.0.0"

# --------------------------------------------------------------- dependencies
DependsRate = Depends(rate_limit)

# reads: open by default, gated when AUTH_REQUIRE_READ=true
READ = [DependsRate, Depends(require_read)]
# writes: authenticated analyst/admin (open only when auth is inactive)
WRITE = [DependsRate, Depends(require_role("analyst"))]
# destructive admin operations (sandbox reset)
ADMIN = [DependsRate, Depends(require_role("admin"))]


# ---------------------------------------------------------------------- health
@router.get("/health", response_model=HealthResponse, dependencies=[DependsRate])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=VERSION,
        database=STORE.persistence.mode,
        ai_provider="local-analysis-engine" if not settings.llm_enabled else f"{settings.ai_provider}:{settings.ai_model}",
        ml_backend=DETECTOR.backend,
        uptime_seconds=round(time.time() - STARTED_AT, 1),
    )


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard", response_model=Dashboard, dependencies=READ)
def dashboard() -> Dashboard:
    return ENGINE.dashboard()


@router.get("/network", response_model=Network, dependencies=READ)
def network() -> Network:
    return ENGINE.network()


# --------------------------------------------------------------------- events
@router.get("/events", dependencies=READ)
def events(
    limit: int = Query(120, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    event_type: str = Query(""),
) -> dict[str, Any]:
    items = STORE.list_events(limit=limit, offset=offset, event_type=event_type)
    return {"items": items, "total": len(STORE.events), "analyzed": STORE.events_analyzed}


@router.get("/events/stream", dependencies=READ)
def event_stream() -> StreamingResponse:
    """Server-sent events feed. Frontend falls back to polling when unavailable."""

    def gen():
        last_count = len(STORE.events)
        yield "event: open\ndata: {}\n\n"
        while True:
            time.sleep(1.0)
            current = list(STORE.events)[-30:]
            if len(STORE.events) != last_count:
                last_count = len(STORE.events)
                import json

                payload = json.dumps({"events": current[-10:], "analyzed": STORE.events_analyzed})
                yield f"data: {payload}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# -------------------------------------------------------------------- threats
@router.get("/threats", dependencies=READ)
def threats(limit: int = Query(50, ge=1, le=300)) -> dict[str, Any]:
    items = STORE.list_threats(limit)
    return {"items": [t.model_dump(mode="json") for t in items], "total": len(STORE.threats)}


# ------------------------------------------------------------------ incidents
@router.get("/incidents", dependencies=READ)
def incidents(status: str = Query("")) -> dict[str, Any]:
    items = STORE.list_incidents()
    if status:
        items = [i for i in items if i.status.value == status.upper()]
    return {"items": [i.model_dump(mode="json") for i in items], "total": len(STORE.incidents)}


@router.get("/incidents/{incident_id}", dependencies=READ)
def incident_detail(incident_id: str) -> dict[str, Any]:
    inc = STORE.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident": inc.model_dump(mode="json"),
        "attack_graph": STORE.get_graph(incident_id),
    }


class StatusBody(BaseModel):
    status: str = Field(..., min_length=3, max_length=20)


@router.patch("/incidents/{incident_id}/status", dependencies=WRITE)
def set_status(incident_id: str, body: StatusBody, request: Request,
               user: dict[str, Any] = Depends(require_role("analyst"))) -> dict[str, Any]:
    try:
        parsed = IncidentStatus(body.status.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid status '{body.status}'")
    inc = STORE.set_incident_status(incident_id, parsed)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    audit(
        "incident.status_changed",
        user=user,
        resource=incident_id,
        detail={"status": parsed.value},
        ip=client_ip(request),
    )
    return {"incident": inc.model_dump(mode="json")}


@router.post("/incidents/{incident_id}/contain", response_model=ContainmentResult, dependencies=WRITE)
def contain(incident_id: str, request: Request,
            user: dict[str, Any] = Depends(require_role("analyst"))) -> ContainmentResult:
    result = ENGINE.contain(incident_id, actor=user.get("email", "analyst"))
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    audit(
        "incident.contained",
        user=user,
        resource=incident_id,
        detail={"actions": result.actions},
        ip=client_ip(request),
    )
    return result


# ------------------------------------------------------------ attack graph
@router.get("/attack-graph", dependencies=READ)
def attack_graphs() -> dict[str, Any]:
    graphs = STORE.list_graphs()
    return {"items": graphs, "total": len(graphs)}


@router.get("/attack-graph/{incident_id}", dependencies=READ)
def attack_graph(incident_id: str) -> dict[str, Any]:
    graph = STORE.get_graph(incident_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Attack graph not found for this incident")
    return graph


# ---------------------------------------------------------------- simulations
@router.get("/scenarios", dependencies=READ)
def scenarios() -> dict[str, Any]:
    return {"items": SCENARIO_META}


@router.post("/simulate/{scenario_key}", response_model=SimulationResult, dependencies=WRITE)
def simulate(scenario_key: str, body: SimulationRequest | None = None) -> SimulationResult:
    from app.simulator.scenarios import SCENARIOS

    if scenario_key not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_key}'")
    req = body or SimulationRequest()
    try:
        return ENGINE.run_scenario(scenario_key, req.intensity, req.target)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}")


# --------------------------------------------------------------------- analyze
@router.post("/analyze", response_model=AnalyzeResponse, dependencies=WRITE)
def analyze_incident(body: AnalyzeRequest) -> AnalyzeResponse:
    inc = STORE.get_incident(body.incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    analysis = analyze(inc, body.question)
    inc.analysis = analysis
    STORE.add_incident(inc)
    return AnalyzeResponse(analysis=analysis, incident=inc)


# --------------------------------------------------------------------- report
def build_report(incident_id: str) -> dict[str, Any]:
    inc = STORE.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if inc.analysis is None:
        inc.analysis = analyze(inc)
        STORE.add_incident(inc)
    graph = STORE.get_graph(incident_id)
    threat = STORE.threats.get(inc.threat_ids[0]) if inc.threat_ids else None
    report = {
        "id": f"RPT-{incident_id.split('-')[-1]}",
        "incident_id": incident_id,
        "title": f"{inc.threat_type} — {', '.join(inc.affected_assets)}",
        "generated_at": time.time(),
        "generated_by": "CyberVerse AI Detection Engine",
        "classification": "INTERNAL — SIMULATED EXERCISE DATA",
        "executive_summary": inc.analysis.summary,
        "threat_type": inc.threat_type,
        "severity": inc.severity.value,
        "risk_score": inc.risk_score,
        "status": inc.status.value,
        "first_seen": inc.first_seen,
        "last_seen": inc.last_seen,
        "source": inc.source,
        "affected_assets": inc.affected_assets,
        "evidence": inc.evidence,
        "timeline": sorted(inc.timeline, key=lambda t: t.get("time", 0)),
        "ai_analysis": inc.analysis.model_dump(mode="json"),
        "recommendations": [r.model_dump() for r in inc.recommendations],
        "containment": inc.containment,
        "attack_path": graph.get("path_labels", []) if graph else [],
        "threat_detail": threat.model_dump(mode="json") if threat else None,
        "notice": "This report was generated from simulated telemetry inside the CyberVerse sandbox.",
    }
    STORE.reports[incident_id] = report
    return report


@router.get("/reports/{incident_id}", dependencies=READ)
def report(incident_id: str) -> dict[str, Any]:
    return build_report(incident_id)


# ----------------------------------------------------------------------- demo
@router.get("/demo", dependencies=READ)
def demo_status() -> dict[str, Any]:
    return DEMO.snapshot()


@router.post("/demo/start", dependencies=WRITE)
def demo_start(request: Request, user: dict[str, Any] = Depends(require_role("analyst"))) -> dict[str, Any]:
    ENGINE.seed()
    result = DEMO.start()
    audit("demo.started", user=user, ip=client_ip(request))
    return result


@router.post("/demo/reset", dependencies=WRITE)
def demo_reset(request: Request, user: dict[str, Any] = Depends(require_role("analyst"))) -> dict[str, Any]:
    result = DEMO.reset()
    audit("demo.reset", user=user, detail=result, ip=client_ip(request))
    return result


@router.post("/demo/stop", dependencies=WRITE)
def demo_stop(request: Request, user: dict[str, Any] = Depends(require_role("analyst"))) -> dict[str, Any]:
    result = DEMO.stop()
    audit("demo.stopped", user=user, ip=client_ip(request))
    return result


# ------------------------------------------------------------------- settings
@router.get("/settings", dependencies=READ)
def public_settings() -> dict[str, Any]:
    """Non-secret runtime configuration exposed to the frontend."""
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "database": STORE.persistence.mode,
        "auth_enabled": settings.auth_active,
        "roles": ["viewer", "analyst", "admin"],
        "demo_mode": True,
        "llm_enabled": settings.llm_enabled,
        "ai_provider": "local-analysis-engine" if not settings.llm_enabled else settings.ai_provider,
        "ai_model": None if not settings.llm_enabled else settings.ai_model,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "ml_backend": DETECTOR.backend,
        "assets": len(topology.NODES),
    }


@router.post("/reset", dependencies=ADMIN)
def reset_sandbox(request: Request, user: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    """Full sandbox reset - clears events, incidents and node states."""
    STORE.full_reset()
    ENGINE.seed()
    audit("sandbox.reset", user=user, ip=client_ip(request))
    return {"status": "reset", "message": "Sandbox restored to baseline state"}
