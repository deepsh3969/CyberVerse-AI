/**
 * Offline fallback dataset.
 *
 * Used ONLY when the backend cannot be reached, so the interface still renders
 * with believable content. Every value is static/derived - no fake live claims.
 */

const now = () => Date.now() / 1000

const node = (id, label, type, zone, ip, x, y, z, description) => ({
  id,
  label,
  type,
  zone,
  ip,
  status: 'healthy',
  risk: 10,
  description,
  position: [x, y, z],
})

const NODES = [
  node('internet', 'Internet', 'cloud', 'external', '0.0.0.0/0', -9, 3.2, -4, 'Untrusted public network origin for inbound traffic.'),
  node('users', 'User Devices', 'client', 'internal', '10.20.0.0/16', -9, -3.4, 5, 'Managed employee workstations and mobile devices.'),
  node('vpn', 'Remote Access Gateway', 'gateway', 'dmz', '10.20.4.5', -6, -0.5, 3.2, 'VPN concentrator used by remote employees.'),
  node('firewall', 'Perimeter Firewall', 'firewall', 'dmz', '10.20.0.1', -3.6, 0.4, -0.4, 'Edge firewall enforcing north-south traffic policy.'),
  node('web', 'Web Server', 'server', 'dmz', '10.20.1.10', 0, 3.4, -3.4, 'Public facing web application server.'),
  node('api', 'API Server', 'server', 'internal', '10.20.1.20', 0.4, 0.2, 0.6, 'Internal REST API consumed by the web tier.'),
  node('auth', 'Authentication Server', 'server', 'internal', '10.20.1.30', 0, -3.4, 3.6, 'Identity provider issuing sessions and tokens.'),
  node('db', 'Database', 'database', 'internal', '10.20.2.10', 4.4, -1.6, 0.2, 'Primary customer data store - crown jewel asset.'),
  node('soc', 'Security Operations Center', 'security', 'management', '10.20.9.10', 4.4, 4, 5, 'Monitoring, alerting and incident response console.'),
  node('ai', 'AI Security Engine', 'ai', 'management', '10.20.9.20', 8, 1.2, -3.2, 'Anomaly detection and threat classification service.'),
]

const edge = (source, target, label) => ({ source, target, label, status: 'idle' })

const EDGES = [
  edge('internet', 'firewall', 'inbound'),
  edge('users', 'vpn', 'remote access'),
  edge('users', 'web', 'https'),
  edge('vpn', 'firewall', 'tunnel'),
  edge('firewall', 'web', 'http'),
  edge('web', 'api', 'rest'),
  edge('api', 'auth', 'tokens'),
  edge('api', 'db', 'sql'),
  edge('auth', 'db', 'identity'),
  edge('soc', 'firewall', 'telemetry'),
  edge('soc', 'db', 'audit'),
  edge('ai', 'soc', 'correlation'),
  edge('ai', 'auth', 'behavior'),
  edge('ai', 'web', 'traffic'),
]

const trend = (base, spread, n = 12) => {
  const t = now()
  return Array.from({ length: n }, (_, i) => ({
    time: t - (n - 1 - i) * 300,
    benign: Math.round(base + Math.sin(i / 1.7) * spread + (i % 3) * 3),
    threat: Math.max(0, Math.round(2 + Math.cos(i / 2.1) * 2 + (i > 7 ? 3 : 0))),
  }))
}

export const FALLBACK_DASHBOARD = {
  security_score: 93,
  threat_level: { level: 'LOW', score: 7, color: '#2fd98a' },
  active_incidents: 1,
  protected_assets: 10,
  events_analyzed: 260,
  threats_blocked: 47,
  events_over_time: trend(24, 8),
  threat_categories: [
    { name: 'Suspicious Login', value: 1 },
    { name: 'Port Scan', value: 1 },
  ],
  risk_history: Array.from({ length: 24 }, (_, i) => ({
    time: now() - (23 - i) * 300,
    score: 92 - (i % 4),
  })),
  event_volume: Array.from({ length: 15 }, (_, i) => ({
    time: now() - (14 - i) * 60,
    count: 8 + ((i * 5) % 11),
  })),
  severity_distribution: [
    { severity: 'LOW', count: 1 },
    { severity: 'MEDIUM', count: 2 },
    { severity: 'HIGH', count: 1 },
    { severity: 'CRITICAL', count: 0 },
  ],
  recent_threats: [],
  top_assets: [
    { asset: 'Authentication Server', risk: 48, status: 'warning' },
    { asset: 'Remote Access Gateway', risk: 44, status: 'warning' },
    { asset: 'Perimeter Firewall', risk: 42, status: 'healthy' },
    { asset: 'Database', risk: 24, status: 'healthy' },
    { asset: 'API Server', risk: 22, status: 'healthy' },
  ],
}

export const FALLBACK_NETWORK = {
  nodes: NODES.map((n, i) => ({
    ...n,
    status: n.id === 'vpn' || n.id === 'auth' ? 'warning' : 'healthy',
    risk: n.id === 'auth' ? 48 : n.id === 'vpn' ? 44 : 10 + i,
  })),
  edges: EDGES,
  updated_at: now(),
}

const ev = (event_type, source, destination, severity, message, ago, metadata = {}) => ({
  id: `EVT-F${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
  event_type,
  source,
  destination,
  severity,
  message,
  timestamp: now() - ago,
  metadata,
})

export const FALLBACK_EVENTS = [
  ev('AUTH_LOGIN_SUCCESS', '10.20.0.41', 'auth', 'INFO', 'Interactive login accepted', 42),
  ev('HTTP_REQUEST', '10.20.0.87', 'web', 'INFO', 'GET /dashboard 200', 38),
  ev('API_CALL', '10.20.0.12', 'api', 'INFO', 'GET /api/v1/status 200', 31),
  ev('SUSPICIOUS_LOGIN', '203.0.113.77', 'auth', 'MEDIUM', 'Login from unseen device and region', 24, {
    new_device: true,
    guaranteed: true,
  }),
  ev('NETWORK_ANOMALY', '198.51.100.90', 'firewall', 'MEDIUM', 'Reconnaissance pattern observed', 18),
  ev('AUTH_LOGIN_FAILED', '198.51.100.90', 'auth', 'MEDIUM', 'Invalid credentials for user j.reyes', 12),
  ev('HEARTBEAT', '10.20.9.10', 'soc', 'INFO', 'Agent telemetry received', 6),
  ev('DNS_QUERY', '10.20.0.64', 'firewall', 'INFO', 'Resolved cdn.internal', 3),
]

export const FALLBACK_INCIDENTS = [
  {
    id: 'INC-OFFLINE1',
    threat_type: 'Suspicious Login',
    severity: 'MEDIUM',
    risk_score: 66,
    status: 'INVESTIGATING',
    first_seen: now() - 640,
    last_seen: now() - 430,
    affected_assets: ['Authentication Server', 'Remote Access Gateway'],
    source: '203.0.113.77',
    destination: 'auth',
    evidence: [
      'Sign-in from a device never previously observed',
      'Geographic hop inconsistent with prior session history',
      '46 profile API calls within 3 minutes of the login',
    ],
    timeline: [
      { time: now() - 640, kind: 'SUSPICIOUS_LOGIN', label: 'Login from unseen device and region', detail: '203.0.113.77 → Remote Access Gateway' },
      { time: now() - 550, kind: 'detect', label: 'AI detection engine raised a threat', detail: 'Suspicious Login · confidence 0.89 · risk 66' },
      { time: now() - 430, kind: 'API_CALL', label: 'Rapid enumeration of user profile endpoints', detail: '203.0.113.77 → API Server' },
    ],
    threat_ids: ['THR-OFFLINE1'],
    recommendations: [
      { title: 'Force step-up authentication', detail: 'Challenge the active session with MFA or terminate it (simulated).', priority: 'HIGH' },
      { title: 'Validate the user', detail: 'Out-of-band confirmation with the account owner before restoring access.', priority: 'HIGH' },
      { title: 'Review session activity', detail: 'Inspect API calls made since the anomalous sign-in.', priority: 'MEDIUM' },
    ],
    analysis: null,
    containment: null,
  },
  {
    id: 'INC-OFFLINE0',
    threat_type: 'Port Scan',
    severity: 'MEDIUM',
    risk_score: 57,
    status: 'RESOLVED',
    first_seen: now() - 1400,
    last_seen: now() - 1340,
    affected_assets: ['Perimeter Firewall'],
    source: '198.51.100.90',
    destination: 'firewall',
    evidence: ['11 distinct ports probed from 198.51.100.90', 'Sequential service enumeration against Perimeter Firewall'],
    timeline: [
      { time: now() - 1400, kind: 'NETWORK_PORT_SCAN', label: 'Sequential SYN probes detected', detail: '198.51.100.90 → Perimeter Firewall' },
      { time: now() - 1180, kind: 'contain', label: 'THREAT CONTAINED', detail: 'Source address blocked (simulated)' },
    ],
    threat_ids: ['THR-OFFLINE0'],
    recommendations: [{ title: 'Enable automatic rate limiting', detail: 'Throttle SYN packets per source at the perimeter firewall (simulated).', priority: 'MEDIUM' }],
    analysis: null,
    containment: { at: now() - 1180, by: 'analyst', actions: ['Source address blocked (simulated)'], mode: 'simulation' },
  },
]

export const FALLBACK_SCENARIOS = [
  { key: 'port-scan', name: 'Port Scan Simulation', severity: 'MEDIUM', description: 'External reconnaissance enumerating exposed services.' },
  { key: 'brute-force', name: 'Brute Force Simulation', severity: 'HIGH', description: 'Repeated credential guessing against the identity provider.' },
  { key: 'suspicious-login', name: 'Suspicious Login Simulation', severity: 'MEDIUM', description: 'Anomalous device, geography and hour on a valid account.' },
  { key: 'privilege-escalation', name: 'Privilege Escalation Simulation', severity: 'HIGH', description: 'Service account abused to gain root and persistence.' },
  { key: 'data-exfiltration', name: 'Data Exfiltration Simulation', severity: 'CRITICAL', description: 'Customer data staged and pushed off network.' },
  { key: 'malware', name: 'Malware-Like File Activity', severity: 'CRITICAL', description: 'Packed payload dropped with a C2 callback attempt.' },
  { key: 'ddos', name: 'DDoS-Like Traffic Spike', severity: 'HIGH', description: 'Distributed request flood against the public web tier.' },
  { key: 'insider-anomaly', name: 'Insider Anomaly Simulation', severity: 'HIGH', description: 'Out-of-role bulk data access by an internal user.' },
]

export const FALLBACK_DEMO_STEPS = [
  ['Normal network baseline', 'All assets healthy, telemetry flowing at expected rates.'],
  ['Suspicious traffic begins', 'Reconnaissance probes arrive at the perimeter.'],
  ['Multiple failed logins', 'Credential guessing escalates against the identity provider.'],
  ['AI detects anomaly', 'Isolation Forest and the rule engine correlate the sequence.'],
  ['Threat visible in 3D network', 'Affected nodes change state on the cyber map.'],
  ['Incident generated', 'Case opened with severity, risk score and evidence.'],
  ['Attack graph reconstructed', 'Lateral path from attacker to crown-jewel data.'],
  ['AI analyst explanation', 'Structured analysis of what, why, evidence and impact.'],
  ['Recommended actions', 'Contextual defensive playbook attached to the incident.'],
  ['Containment requested', 'Analyst triggers simulated containment.'],
  ['Threat contained', 'Session terminated, path blocked, endpoint isolated.'],
  ['Recovery', 'Assets return to a monitored, secure state.'],
].map(([label, detail], index) => ({ index, label, detail }))

export const FALLBACK_DEMO = {
  state: 'idle',
  step: -1,
  label: '',
  detail: '',
  started_at: null,
  incident_id: null,
  scenario: 'brute-force',
  steps: FALLBACK_DEMO_STEPS,
}

export const FALLBACK_SETTINGS = {
  app: 'CyberVerse AI',
  environment: 'offline-preview',
  database: 'disabled',
  demo_mode: true,
  llm_enabled: false,
  ai_provider: 'local-analysis-engine',
  ai_model: null,
  rate_limit_per_minute: 240,
  ml_backend: 'isolation-forest',
  assets: 10,
}
