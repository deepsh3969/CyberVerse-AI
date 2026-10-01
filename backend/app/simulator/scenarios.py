"""Safe, synthetic cyber-attack scenario generator.

Every event produced here is fabricated inside the application sandbox.
No packet is ever sent anywhere: these are pure in-memory records that feed
the detection engine. Source addresses use RFC 5737 documentation ranges.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable

from app.services.store import new_id

TEST_NET_1 = "198.51.100."  # RFC 5737 documentation range - non routable
TEST_NET_2 = "203.0.113."


def _ts(offset: float) -> float:
    return time.time() + offset


def make_event(
    event_type: str,
    source: str,
    destination: str,
    severity: str,
    message: str,
    timestamp: float,
    metadata: dict | None = None,
) -> dict:
    return {
        "id": new_id("EVT"),
        "event_type": event_type,
        "source": source,
        "destination": destination,
        "severity": severity,
        "message": message,
        "timestamp": round(timestamp, 3),
        "metadata": metadata or {},
    }


@dataclass
class ScenarioOutput:
    key: str
    name: str
    events: list[dict] = field(default_factory=list)
    attack_path: list[str] = field(default_factory=list)
    summary: str = ""


Intensity = str
Builder = Callable[[Intensity, str], ScenarioOutput]


# --------------------------------------------------------------------- helpers
def _scale(intensity: Intensity) -> int:
    return {"low": 1, "normal": 2, "high": 3}.get(intensity, 2)


def _attacker(seed_index: int = 0) -> str:
    return f"{TEST_NET_2}{(44 + seed_index) % 250}"


# ------------------------------------------------------------------ scenarios
def port_scan(intensity: Intensity, target: str) -> ScenarioOutput:
    scale = _scale(intensity)
    src = _attacker()
    dst = target or "firewall"
    ports = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 3306, 3389, 8080, 8443, 9200]
    events = []
    step = 0.45 / scale
    for i, port in enumerate(ports[: 9 + 3 * scale]):
        events.append(
            make_event(
                "NETWORK_PORT_SCAN",
                src,
                dst,
                "MEDIUM",
                f"TCP SYN probe to port {port}",
                _ts(i * step),
                {"port": port, "proto": "tcp", "syn": True, "guaranteed": True,
                 "evidence": [f"Sequential SYN scan covering {len(ports[:9 + 3 * scale])} ports",
                              f"Source {src} enumerated services on {dst} without completing handshakes"]},
            )
        )
    events.append(
        make_event(
            "NETWORK_ANOMALY",
            src,
            dst,
            "HIGH",
            "Reconnaissance pattern confirmed by heuristic engine",
            _ts(len(events) * step),
            {"guaranteed": True, "evidence": ["Scan rate exceeds baseline by 40x", "Target set spans common admin ports"]},
        )
    )
    return ScenarioOutput(
        "port-scan",
        "Port Scan Simulation",
        events,
        ["attacker", "internet", "firewall", "web"],
        "External host enumerated exposed services across the perimeter.",
    )


def brute_force(intensity: Intensity, target: str) -> ScenarioOutput:
    scale = _scale(intensity)
    src = _attacker(1)
    dst = target or "auth"
    attempts = 4 + 3 * scale
    events = []
    for i in range(attempts):
        events.append(
            make_event(
                "AUTH_LOGIN_FAILED",
                src,
                dst,
                "MEDIUM",
                f"Invalid credentials for user j.reyes (attempt {i + 1})",
                _ts(i * 0.6),
                {"user": "j.reyes", "method": "password", "attempt": i + 1,
                 "evidence": [f"{attempts} failed login attempts from {src}",
                              "Password authentication retried without lockout delay"]},
            )
        )
    events.append(
        make_event(
            "AUTH_LOGIN_SUCCESS",
            src,
            dst,
            "HIGH",
            "Session established for user j.reyes after repeated failures",
            _ts(attempts * 0.6 + 0.4),
            {"user": "j.reyes", "new_session": True, "mfa": False, "guaranteed": True,
             "evidence": ["Successful login immediately after repeated failures",
                          "No MFA challenge satisfied on the accepted session"]},
        )
    )
    events.append(
        make_event(
            "AUTH_TOKEN_ISSUED",
            src,
            "db",
            "HIGH",
            "Privileged token issued to newly authenticated session",
            _ts(attempts * 0.6 + 0.9),
            {"user": "j.reyes", "scope": "read:customers"},
        )
    )
    return ScenarioOutput(
        "brute-force",
        "Brute Force Simulation",
        events,
        ["attacker", "internet", "vpn", "firewall", "auth", "account", "db"],
        "Credential attack against the identity provider ending in a successful session.",
    )


def suspicious_login(intensity: Intensity, target: str) -> ScenarioOutput:
    src = _attacker(2)
    dst = target or "auth"
    events = [
        make_event(
            "SUSPICIOUS_LOGIN",
            src,
            dst,
            "MEDIUM",
            "Successful login from unseen device and unusual geography",
            _ts(0),
            {"user": "a.novak", "new_device": True, "geo": "outside-home-region",
             "guaranteed": True,
             "evidence": ["Sign-in from a device never previously observed",
                          "Geographic hop inconsistent with prior session history",
                          "Login occurred outside normal working hours"]},
        ),
        make_event(
            "AUTH_LOGIN_SUCCESS",
            src,
            dst,
            "MEDIUM",
            "Session accepted for user a.novak",
            _ts(1.2),
            {"user": "a.novak", "mfa": False, "new_session": True},
        ),
        make_event(
            "API_CALL",
            src,
            "api",
            "MEDIUM",
            "Rapid enumeration of user profile endpoints",
            _ts(3.0),
            {"requests": 46, "path": "/api/v1/users/*", "status": 200},
        ),
    ]
    return ScenarioOutput(
        "suspicious-login",
        "Suspicious Login Simulation",
        events,
        ["attacker", "internet", "vpn", "auth", "account"],
        "Anomalous but successful authentication followed by bulk profile reads.",
    )


def privilege_escalation(intensity: Intensity, target: str) -> ScenarioOutput:
    src = _attacker(3)
    dst = target or "api"
    events = [
        make_event(
            "AUTH_LOGIN_SUCCESS",
            src,
            dst,
            "LOW",
            "Low-privilege service account session opened",
            _ts(0),
            {"user": "svc_reports", "mfa": False},
        ),
        make_event(
            "PRIVILEGE_ESCALATION",
            src,
            dst,
            "HIGH",
            "sudo execution abused to obtain root shell",
            _ts(1.5),
            {"user": "svc_reports", "technique": "sudo-abuse", "guaranteed": True,
             "evidence": ["Service account executed sudo without approval workflow",
                          "Root shell spawned from a batch workload identity"]},
        ),
        make_event(
            "PRIVILEGE_ESCALATION",
            src,
            dst,
            "HIGH",
            "Write access granted to systemd unit directory",
            _ts(3.2),
            {"user": "svc_reports", "technique": "persistence", "guaranteed": True},
        ),
        make_event(
            "FILE_SUSPICIOUS",
            src,
            dst,
            "HIGH",
            "New auto-start unit written to /etc/systemd/system",
            _ts(4.4),
            {"path": "/etc/systemd/system/auditd-helper.service", "action": "create"},
        ),
    ]
    return ScenarioOutput(
        "privilege-escalation",
        "Privilege Escalation Simulation",
        events,
        ["attacker", "internet", "firewall", "web", "api", "account"],
        "Service account elevated to root and established persistence.",
    )


def data_exfiltration(intensity: Intensity, target: str) -> ScenarioOutput:
    scale = _scale(intensity)
    src = _attacker(4)
    dst = target or "db"
    chunk_mb = 180 * scale
    events = [
        make_event(
            "AUTH_LOGIN_SUCCESS",
            src,
            "api",
            "MEDIUM",
            "Analytics session authenticated against API tier",
            _ts(0),
            {"user": "etl_reader", "mfa": False},
        ),
        make_event(
            "API_CALL",
            src,
            "api",
            "MEDIUM",
            "Bulk export endpoint invoked outside change window",
            _ts(1.4),
            {"path": "/api/v1/export/customers", "rows": 240000},
        ),
        make_event(
            "DATA_EXFILTRATION",
            dst,
            src,
            "CRITICAL",
            f"{chunk_mb} MB outbound transfer to unrecognized host",
            _ts(3.0),
            {"bytes_out": chunk_mb * 1024 * 1024, "proto": "https", "guaranteed": True,
             "evidence": [f"{chunk_mb} MB egress in under a minute",
                          "Destination host not in the approved vendor allow-list",
                          "Transfer followed a bulk export API call"]},
        ),
        make_event(
            "DATA_EXFILTRATION",
            dst,
            src,
            "CRITICAL",
            "Second egress burst observed on the same flow",
            _ts(6.5),
            {"bytes_out": chunk_mb * 1024 * 1024 * 0.6, "proto": "https"},
        ),
    ]
    return ScenarioOutput(
        "data-exfiltration",
        "Data Exfiltration Simulation",
        events,
        ["attacker", "internet", "firewall", "web", "api", "db"],
        "Customer records staged and pushed off-network in encrypted bursts.",
    )


def malware(intensity: Intensity, target: str) -> ScenarioOutput:
    src = _attacker(5)
    dst = target or "web"
    events = [
        make_event(
            "HTTP_REQUEST",
            src,
            dst,
            "LOW",
            "Request with crafted upload field accepted",
            _ts(0),
            {"method": "POST", "path": "/upload", "status": 200},
        ),
        make_event(
            "MALWARE_FILE_ACTIVITY",
            src,
            dst,
            "CRITICAL",
            "Obfuscated executable written to web root",
            _ts(1.6),
            {"path": "/var/www/assets/upd_cache.php", "entropy": 7.9, "guaranteed": True,
             "evidence": ["Double-encoded payload written to a served directory",
                          "File entropy 7.9 indicates packed/encrypted content",
                          "No corresponding deployment ticket exists"]},
        ),
        make_event(
            "MALWARE_FILE_ACTIVITY",
            src,
            "api",
            "HIGH",
            "Outbound callback attempt to dynamic DNS host",
            _ts(4.0),
            {"domain": "sync-node-44.example-dns.net", "action": "connect",
             "evidence": ["Beacon attempt at 20s intervals to a freshly registered domain"]},
        ),
    ]
    return ScenarioOutput(
        "malware",
        "Malware-Like File Activity",
        events,
        ["attacker", "internet", "firewall", "web", "api"],
        "Dropper wrote a packed script and attempted command-and-control callback.",
    )


def ddos(intensity: Intensity, target: str) -> ScenarioOutput:
    scale = _scale(intensity)
    dst = target or "web"
    rng = random.Random(1234)
    events = []
    count = 22 + 14 * scale
    for i in range(count):
        src = f"{TEST_NET_1}{rng.randint(2, 250)}"
        events.append(
            make_event(
                "HTTP_REQUEST",
                src,
                dst,
                "LOW" if i < count - 2 else "HIGH",
                f"GET / (status 503) request #{i + 1}",
                _ts(i * 0.06),
                {"method": "GET", "path": "/", "status": 503, "rps": 4200 * scale},
            )
        )
    events.append(
        make_event(
            "NETWORK_TRAFFIC_SPIKE",
            "botnet-aggregate",
            dst,
            "HIGH",
            f"Request rate {4200 * scale} rps - {30 * scale}x baseline",
            _ts(count * 0.06 + 0.3),
            {"requests_per_sec": 4200 * scale, "guaranteed": True,
             "evidence": [f"Request rate reached {4200 * scale} rps against {dst}",
                          "Traffic distributed across many source addresses",
                          "Origin returned 503 for sustained periods"]},
        )
    )
    return ScenarioOutput(
        "ddos",
        "DDoS-Like Traffic Spike",
        events,
        ["botnet", "internet", "firewall", "web"],
        "Distributed request flood exhausted the web tier.",
    )


def insider_anomaly(intensity: Intensity, target: str) -> ScenarioOutput:
    src = "usr-maya@corp"
    dst = target or "db"
    events = [
        make_event(
            "INSIDER_ANOMALY",
            src,
            dst,
            "HIGH",
            "Database query volume 12x personal baseline at 02:14 local",
            _ts(0),
            {"user": "maya.torres", "queries": 1840, "hour": 2, "guaranteed": True,
             "evidence": ["1,840 customer table reads in 9 minutes",
                          "Access occurred at 02:14 outside assigned shift",
                          "Volume is 12x this user's 30-day baseline"]},
        ),
        make_event(
            "API_CALL",
            src,
            "api",
            "MEDIUM",
            "Bulk download via internal reporting API",
            _ts(2.4),
            {"path": "/api/v1/reports/all", "requests": 61},
        ),
        make_event(
            "DATA_EGRESS",
            src,
            "vpn",
            "MEDIUM",
            "Large archive synced to personal cloud storage",
            _ts(5.0),
            {"bytes_out": 940 * 1024 * 1024, "dest": "personal-cloud"},
        ),
    ]
    return ScenarioOutput(
        "insider-anomaly",
        "Insider Anomaly Simulation",
        events,
        ["insider", "users", "vpn", "auth", "db"],
        "Privileged employee pulled far more data than their role requires.",
    )


SCENARIOS: dict[str, Builder] = {
    "port-scan": port_scan,
    "brute-force": brute_force,
    "suspicious-login": suspicious_login,
    "privilege-escalation": privilege_escalation,
    "data-exfiltration": data_exfiltration,
    "malware": malware,
    "ddos": ddos,
    "insider-anomaly": insider_anomaly,
}

SCENARIO_META = [
    {"key": "port-scan", "name": "Port Scan Simulation", "severity": "MEDIUM",
     "description": "External reconnaissance enumerating exposed services."},
    {"key": "brute-force", "name": "Brute Force Simulation", "severity": "HIGH",
     "description": "Repeated credential guessing against the identity provider."},
    {"key": "suspicious-login", "name": "Suspicious Login Simulation", "severity": "MEDIUM",
     "description": "Anomalous device, geography and hour on a valid account."},
    {"key": "privilege-escalation", "name": "Privilege Escalation Simulation", "severity": "HIGH",
     "description": "Service account abused to gain root and persistence."},
    {"key": "data-exfiltration", "name": "Data Exfiltration Simulation", "severity": "CRITICAL",
     "description": "Customer data staged and pushed off network."},
    {"key": "malware", "name": "Malware-Like File Activity", "severity": "CRITICAL",
     "description": "Packed payload dropped with a C2 callback attempt."},
    {"key": "ddos", "name": "DDoS-Like Traffic Spike", "severity": "HIGH",
     "description": "Distributed request flood against the public web tier."},
    {"key": "insider-anomaly", "name": "Insider Anomaly Simulation", "severity": "HIGH",
     "description": "Out-of-role bulk data access by an internal user."},
]


def normal_event(rng: random.Random, offset_seconds: float = 0.0) -> dict:
    kind = rng.choices(
        ["HTTP_REQUEST", "DNS_QUERY", "AUTH_LOGIN_SUCCESS", "API_CALL", "HEARTBEAT", "AUTH_LOGOUT"],
        weights=[34, 20, 14, 16, 12, 4],
    )[0]
    src = f"10.20.0.{rng.randint(10, 240)}"
    dst_map = {
        "HTTP_REQUEST": "web",
        "DNS_QUERY": "firewall",
        "AUTH_LOGIN_SUCCESS": "auth",
        "API_CALL": "api",
        "HEARTBEAT": "soc",
        "AUTH_LOGOUT": "auth",
    }
    messages = {
        "HTTP_REQUEST": "GET /dashboard 200",
        "DNS_QUERY": "Resolved cdn.internal",
        "AUTH_LOGIN_SUCCESS": "Interactive login accepted",
        "API_CALL": "GET /api/v1/status 200",
        "HEARTBEAT": "Agent telemetry received",
        "AUTH_LOGOUT": "Session closed",
    }
    return make_event(
        kind,
        src,
        dst_map[kind],
        "INFO",
        messages[kind],
        _ts(offset_seconds - rng.uniform(0, 1800)),
        {"baseline": True},
    )


def seed_events(count: int = 260) -> list[dict]:
    rng = random.Random(2024)
    events = [normal_event(rng) for _ in range(count)]
    events.sort(key=lambda e: e["timestamp"])
    return events


def build_scenario(key: str, intensity: Intensity = "normal", target: str = "") -> ScenarioOutput:
    builder = SCENARIOS.get(key)
    if builder is None:
        raise KeyError(f"Unknown scenario: {key}")
    return builder(intensity, target)
