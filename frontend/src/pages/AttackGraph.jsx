import React, { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { GitBranch, Link2, Share2 } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { api } from '../services/api'
import usePoll from '../hooks/usePoll'
import { EmptyState, Panel, SectionHeading, SeverityBadge, StatusDot } from '../components/ui'
import { formatDateTime, relativeTime, riskBand } from '../utils/format'

const NODE_COLORS = {
  compromised: '#ff3b5c',
  monitoring: '#6f8fff',
  warning: '#f5c518',
  contained: '#38d6f5',
  healthy: '#2fd98a',
  attacker: '#ff8a3d',
  account: '#ff3b5c',
}

function GraphCanvas({ graph, selectedId, onSelect }) {
  const nodes = graph.nodes || []
  const edges = graph.edges || []
  const rowH = 88
  const height = 60 + nodes.length * rowH

  const positions = useMemo(() => {
    const map = {}
    nodes.forEach((n, i) => {
      const wobble = i % 2 === 0 ? -1 : 1
      map[n.id] = { x: 260 + wobble * (i === 0 ? 0 : 46), y: 48 + i * rowH }
    })
    return map
  }, [nodes, rowH])

  return (
    <svg viewBox={`0 0 520 ${height}`} className="w-full" style={{ maxHeight: 620 }} role="img" aria-label="Attack path graph">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#ff3b5c" />
        </marker>
        <linearGradient id="edgeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ff3b5c" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#ff8a3d" stopOpacity="0.55" />
        </linearGradient>
      </defs>

      {edges.map((e, i) => {
        const a = positions[e.source]
        const b = positions[e.target]
        if (!a || !b) return null
        const midY = (a.y + b.y) / 2
        return (
          <path
            key={i}
            d={`M ${a.x} ${a.y + 26} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y - 26}`}
            fill="none"
            stroke={e.active ? 'url(#edgeGrad)' : '#24354f'}
            strokeWidth={e.active ? 2.4 : 1.6}
            strokeDasharray={e.active ? '7 5' : '0'}
            markerEnd={e.active ? 'url(#arrow)' : undefined}
          >
            {e.active && (
              <animate attributeName="stroke-dashoffset" from="24" to="0" dur="0.9s" repeatCount="indefinite" />
            )}
          </path>
        )
      })}

      {nodes.map((n) => {
        const p = positions[n.id]
        if (!p) return null
        const color = NODE_COLORS[n.kind] || NODE_COLORS[n.status] || '#94a3b8'
        const isSel = selectedId === n.id
        return (
          <g
            key={n.id}
            transform={`translate(${p.x}, ${p.y})`}
            onClick={() => onSelect(n)}
            style={{ cursor: 'pointer' }}
            tabIndex={0}
            onKeyDown={(ev) => ev.key === 'Enter' && onSelect(n)}
            role="button"
            aria-label={`Node ${n.label}`}
          >
            <circle r={isSel ? 27 : 24} fill={`${color}22`} stroke={color} strokeWidth={isSel ? 2.4 : 1.6} />
            <circle r={5} fill={color} />
            <text y={-36} textAnchor="middle" fill="#e2e8f0" fontSize="12.5" fontWeight="600" fontFamily="Inter, sans-serif">
              {n.label}
            </text>
            <text y={44} textAnchor="middle" fill="#64748b" fontSize="10" fontFamily="JetBrains Mono, monospace">
              {n.status} · risk {n.risk}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default function AttackGraph() {
  const { incidents, events, offline } = useApp()
  const [params, setParams] = useSearchParams()
  const { data } = usePoll(() => api.attackGraphs(), 5000, { enabled: !offline })
  const graphs = data?.items || []
  const [selectedNodeId, setSelectedNodeId] = useState(null)

  const activeId = params.get('incident')
  const graph = useMemo(() => {
    if (activeId) return graphs.find((g) => g.incident_id === activeId) || null
    return graphs[0] || null
  }, [graphs, activeId])

  useEffect(() => {
    setSelectedNodeId(null)
  }, [graph?.incident_id])

  const incident = incidents.find((i) => i.id === graph?.incident_id)
  const selectedNode = graph?.nodes.find((n) => n.id === selectedNodeId) || null

  const nodeEvents = useMemo(() => {
    if (!selectedNode) return []
    return events.filter((e) => e.destination === selectedNode.id || e.source === selectedNode.id).slice(0, 6)
  }, [selectedNode, events])

  const assessment = useMemo(() => {
    if (!selectedNode) return ''
    if (selectedNode.status === 'compromised')
      return `Compromised during the ${incident?.threat_type || 'attack'} chain. Risk ${selectedNode.risk}/100 — treat as hostile until rebuilt or re-imaged (simulated).`
    if (selectedNode.status === 'contained')
      return 'Isolated by simulated containment. Monitoring continues for related indicators.'
    if (selectedNode.status === 'warning')
      return `Elevated risk (${selectedNode.risk}/100). Reached by the attack path but not confirmed compromised — review authentication and access logs.`
    return `Behaving within baseline (risk ${selectedNode.risk}/100). Adjacent to the attack path, so keep enhanced telemetry on.`
  }, [selectedNode, incident])

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Lateral movement"
        title="Attack Graph"
        description="Reconstructed path from the initial access vector to the target asset, with per-hop status, risk and evidence."
        actions={
          <Link to="/app/network" className="btn-ghost text-xs">
            <Share2 size={14} /> View in 3D
          </Link>
        }
      />

      {graphs.length === 0 ? (
        <EmptyState
          icon={<GitBranch size={24} />}
          title="No attack graphs yet"
          message="An attack graph is reconstructed automatically when a simulation raises an incident."
          action={
            <Link to="/app/simulator" className="btn-primary text-xs">
              Run a simulation
            </Link>
          }
        />
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {graphs.map((g) => (
              <button
                key={g.incident_id}
                onClick={() => setParams({ incident: g.incident_id })}
                className={`rounded-lg border px-3 py-1.5 text-[11.5px] transition ${
                  graph?.incident_id === g.incident_id
                    ? 'border-cyber-400/45 bg-cyber-400/10 text-cyber-300'
                    : 'border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                {g.incident_id}
                <span className="mono ml-2 text-[10px] text-slate-500">{g.path_labels?.length || 0} hops</span>
              </button>
            ))}
          </div>

          <div className="grid gap-3 xl:grid-cols-[1fr_330px]">
            <div className="card p-4">
              <div className="mb-3 flex flex-wrap items-center gap-3 border-b border-white/[0.06] pb-3">
                <div>
                  <p className="label-caps">Active attack path</p>
                  <p className="mt-0.5 text-[13px] text-slate-300">
                    {graph.path_labels?.join('  →  ') || '—'}
                  </p>
                </div>
                {incident && (
                  <div className="ml-auto flex items-center gap-2">
                    <SeverityBadge severity={incident.severity} />
                    <Link to={`/app/incidents/${incident.id}`} className="text-[11.5px] text-cyber-400 hover:text-cyber-300">
                      Open incident →
                    </Link>
                  </div>
                )}
              </div>
              <div className="flex justify-center overflow-x-auto">
                <GraphCanvas graph={graph} selectedId={selectedNodeId} onSelect={(n) => setSelectedNodeId(n.id)} />
              </div>
              <p className="mono mt-2 text-center text-[10px] uppercase tracking-wider text-slate-600">
                click a node for details · dashed red edges = attacker-controlled traversal
              </p>
            </div>

            <div className="space-y-3">
              <Panel title="Node details" subtitle="Hop-level forensics">
                {!selectedNode ? (
                  <EmptyState
                    icon={<Link2 size={20} />}
                    title="Select a hop"
                    message="Click any node in the graph to inspect status, risk, connections and AI assessment."
                  />
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-[15px] font-semibold text-white">{selectedNode.label}</p>
                        <p className="mono text-[11px] uppercase tracking-wider text-slate-500">{selectedNode.kind}</p>
                      </div>
                      <span className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-400">
                        <StatusDot status={selectedNode.status} /> {selectedNode.status}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-lg border border-white/[0.07] p-2.5">
                        <p className="label-caps">Risk</p>
                        <p className="mono mt-1 text-sm" style={{ color: riskBand(selectedNode.risk).color }}>
                          {selectedNode.risk}/100
                        </p>
                      </div>
                      <div className="rounded-lg border border-white/[0.07] p-2.5">
                        <p className="label-caps">Reached</p>
                        <p className="mono mt-1 text-[12px] text-slate-200">
                          {selectedNode.compromised_at ? formatDateTime(selectedNode.compromised_at) : 'not reached'}
                        </p>
                      </div>
                    </div>

                    <div>
                      <p className="label-caps mb-1">Connections in path</p>
                      <p className="text-[12.5px] text-slate-400">
                        {graph.edges
                          .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                          .map((e) =>
                            e.source === selectedNode.id
                              ? graph.nodes.find((n) => n.id === e.target)?.label
                              : graph.nodes.find((n) => n.id === e.source)?.label,
                          )
                          .filter(Boolean)
                          .join(', ') || 'endpoint of the path'}
                      </p>
                    </div>

                    <div>
                      <p className="label-caps mb-1">Recent events</p>
                      {nodeEvents.length === 0 ? (
                        <p className="text-[12px] text-slate-500">No events recorded for this hop.</p>
                      ) : (
                        <ul className="space-y-1">
                          {nodeEvents.map((e) => (
                            <li key={e.id} className="mono truncate text-[11px] text-slate-500">
                              {relativeTime(e.timestamp)} · {e.event_type}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>

                    <div className="rounded-lg border border-cyber-400/25 bg-cyber-400/[0.05] p-3">
                      <p className="label-caps mb-1 text-cyber-300">AI assessment</p>
                      <p className="text-[12.5px] leading-relaxed text-slate-300">{assessment}</p>
                    </div>
                  </div>
                )}
              </Panel>

              {incident && (
                <Panel title="Incident context">
                  <div className="space-y-2 text-[12.5px]">
                    <div className="flex justify-between"><span className="label-caps">Type</span><span className="text-slate-200">{incident.threat_type}</span></div>
                    <div className="flex justify-between"><span className="label-caps">Severity</span><span className="text-slate-200">{incident.severity}</span></div>
                    <div className="flex justify-between"><span className="label-caps">Status</span><span className="text-slate-200">{incident.status}</span></div>
                    <div className="flex justify-between"><span className="label-caps">Source</span><span className="mono text-slate-200">{incident.source}</span></div>
                    <div className="flex justify-between gap-3">
                      <span className="label-caps shrink-0">Affected</span>
                      <span className="text-right text-slate-300">{incident.affected_assets?.join(', ')}</span>
                    </div>
                  </div>
                </Panel>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
