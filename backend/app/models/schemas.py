from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    COMPROMISED = "compromised"
    MONITORING = "monitoring"
    CONTAINED = "contained"


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    RESOLVED = "RESOLVED"


class EventIn(BaseModel):
    event_type: str = Field(..., min_length=2, max_length=64)
    source: str = Field(..., min_length=1, max_length=64)
    destination: str = Field(..., min_length=1, max_length=64)
    severity: Severity = Severity.INFO
    message: str = Field(default="", max_length=500)
    timestamp: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Event(EventIn):
    id: str
    timestamp: float


class Threat(BaseModel):
    id: str
    threat_type: str
    severity: Severity
    risk_score: int = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: float = 0.0
    affected_asset: str
    source: str
    destination: str = ""
    timestamp: float
    evidence: list[str] = Field(default_factory=list)
    detector: str = "hybrid"
    status: str = "ACTIVE"


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: str = "MEDIUM"


class AnalysisSection(BaseModel):
    heading: str
    body: str


class AIAnalysis(BaseModel):
    incident_id: str
    provider: str
    summary: str
    sections: list[AnalysisSection] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    generated_at: float


class Incident(BaseModel):
    id: str
    threat_type: str
    severity: Severity
    risk_score: int
    status: IncidentStatus = IncidentStatus.OPEN
    first_seen: float
    last_seen: float
    affected_assets: list[str] = Field(default_factory=list)
    source: str
    destination: str = ""
    evidence: list[str] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    threat_ids: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    analysis: Optional[AIAnalysis] = None
    containment: Optional[dict[str, Any]] = None


class GraphNode(BaseModel):
    id: str
    label: str
    kind: str = "asset"
    status: NodeStatus = NodeStatus.HEALTHY
    risk: int = 0
    compromised_at: Optional[float] = None
    detail: str = ""


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    active: bool = False
    severity: Severity = Severity.INFO


class AttackGraph(BaseModel):
    incident_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    path_labels: list[str] = Field(default_factory=list)
    created_at: float


class NetworkNode(BaseModel):
    id: str
    label: str
    type: str
    status: NodeStatus = NodeStatus.HEALTHY
    risk: int = 0
    ip: str = ""
    zone: str = "internal"
    description: str = ""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)


class NetworkEdge(BaseModel):
    source: str
    target: str
    label: str = ""
    status: str = "idle"


class Network(BaseModel):
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)
    updated_at: float = 0.0


class ThreatLevel(BaseModel):
    level: str
    score: int
    color: str


class Dashboard(BaseModel):
    security_score: int
    threat_level: ThreatLevel
    active_incidents: int
    protected_assets: int
    events_analyzed: int
    threats_blocked: int
    events_over_time: list[dict[str, Any]] = Field(default_factory=list)
    threat_categories: list[dict[str, Any]] = Field(default_factory=list)
    risk_history: list[dict[str, Any]] = Field(default_factory=list)
    event_volume: list[dict[str, Any]] = Field(default_factory=list)
    severity_distribution: list[dict[str, Any]] = Field(default_factory=list)
    recent_threats: list[Threat] = Field(default_factory=list)
    top_assets: list[dict[str, Any]] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    intensity: str = Field(default="normal", pattern="^(low|normal|high)$")
    target: str = Field(default="", max_length=64)
    replay: bool = True


class SimulationResult(BaseModel):
    scenario: str
    events: list[Event] = Field(default_factory=list)
    threats: list[Threat] = Field(default_factory=list)
    incident: Optional[Incident] = None
    attack_graph: Optional[AttackGraph] = None
    message: str = ""


class AnalyzeRequest(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=64)
    question: str = Field(default="", max_length=400)


class AnalyzeResponse(BaseModel):
    analysis: AIAnalysis
    incident: Optional[Incident] = None


class ContainmentResult(BaseModel):
    incident: Incident
    actions: list[str] = Field(default_factory=list)
    message: str = "THREAT CONTAINED"


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ai_provider: str
    ml_backend: str
    uptime_seconds: float
