"""Static definition of the demo infrastructure topology.

Everything here describes the application's own sandbox. No real hosts.
"""
from __future__ import annotations

NODES = [
    {
        "id": "internet",
        "label": "Internet",
        "type": "cloud",
        "zone": "external",
        "ip": "0.0.0.0/0",
        "description": "Untrusted public network origin for inbound traffic.",
        "position": (-9.0, 3.2, -4.0),
    },
    {
        "id": "users",
        "label": "User Devices",
        "type": "client",
        "zone": "internal",
        "ip": "10.20.0.0/16",
        "description": "Managed employee workstations and mobile devices.",
        "position": (-9.0, -3.4, 5.0),
    },
    {
        "id": "vpn",
        "label": "Remote Access Gateway",
        "type": "gateway",
        "zone": "dmz",
        "ip": "10.20.4.5",
        "description": "VPN concentrator used by remote employees.",
        "position": (-6.0, -0.5, 3.2),
    },
    {
        "id": "firewall",
        "label": "Perimeter Firewall",
        "type": "firewall",
        "zone": "dmz",
        "ip": "10.20.0.1",
        "description": "Edge firewall enforcing north-south traffic policy.",
        "position": (-3.6, 0.4, -0.4),
    },
    {
        "id": "web",
        "label": "Web Server",
        "type": "server",
        "zone": "dmz",
        "ip": "10.20.1.10",
        "description": "Public facing web application server.",
        "position": (0.0, 3.4, -3.4),
    },
    {
        "id": "api",
        "label": "API Server",
        "type": "server",
        "zone": "internal",
        "ip": "10.20.1.20",
        "description": "Internal REST API consumed by the web tier.",
        "position": (0.4, 0.2, 0.6),
    },
    {
        "id": "auth",
        "label": "Authentication Server",
        "type": "server",
        "zone": "internal",
        "ip": "10.20.1.30",
        "description": "Identity provider issuing sessions and tokens.",
        "position": (0.0, -3.4, 3.6),
    },
    {
        "id": "db",
        "label": "Database",
        "type": "database",
        "zone": "internal",
        "ip": "10.20.2.10",
        "description": "Primary customer data store - crown jewel asset.",
        "position": (4.4, -1.6, 0.2),
    },
    {
        "id": "soc",
        "label": "Security Operations Center",
        "type": "security",
        "zone": "management",
        "ip": "10.20.9.10",
        "description": "Monitoring, alerting and incident response console.",
        "position": (4.4, 4.0, 5.0),
    },
    {
        "id": "ai",
        "label": "AI Security Engine",
        "type": "ai",
        "zone": "management",
        "ip": "10.20.9.20",
        "description": "Anomaly detection and threat classification service.",
        "position": (8.0, 1.2, -3.2),
    },
]

EDGES = [
    {"source": "internet", "target": "firewall", "label": "inbound"},
    {"source": "users", "target": "vpn", "label": "remote access"},
    {"source": "users", "target": "web", "label": "https"},
    {"source": "vpn", "target": "firewall", "label": "tunnel"},
    {"source": "firewall", "target": "web", "label": "http"},
    {"source": "web", "target": "api", "label": "rest"},
    {"source": "api", "target": "auth", "label": "tokens"},
    {"source": "api", "target": "db", "label": "sql"},
    {"source": "auth", "target": "db", "label": "identity"},
    {"source": "soc", "target": "firewall", "label": "telemetry"},
    {"source": "soc", "target": "db", "label": "audit"},
    {"source": "ai", "target": "soc", "label": "correlation"},
    {"source": "ai", "target": "auth", "label": "behavior"},
    {"source": "ai", "target": "web", "label": "traffic"},
]

ASSET_SENSITIVITY = {
    "internet": 10,
    "users": 55,
    "vpn": 70,
    "firewall": 95,
    "web": 75,
    "api": 80,
    "auth": 95,
    "db": 100,
    "soc": 90,
    "ai": 85,
}

LABELS = {n["id"]: n["label"] for n in NODES}


def label_of(node_id: str) -> str:
    return LABELS.get(node_id, node_id)


def get_node(node_id: str) -> dict | None:
    for n in NODES:
        if n["id"] == node_id:
            return n
    return None
