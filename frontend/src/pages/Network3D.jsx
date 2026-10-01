import React, { useMemo, useState } from 'react'
import { Crosshair, Info, Pause, Play, RotateCcw, ShieldAlert } from 'lucide-react'
import NetworkScene from '../three/NetworkScene'
import { useApp } from '../context/AppContext'
import {
  DefinitionRow,
  EmptyState,
  Panel,
  SectionHeading,
  SeverityBadge,
  StatusDot,
} from '../components/ui'
import { riskBand, relativeTime } from '../utils/format'

const LEGEND = [
  ['healthy', 'Healthy'],
  ['warning', 'Warning'],
  ['compromised', 'Compromised'],
  ['monitoring', 'Monitoring'],
  ['contained', 'Contained'],
]

export default function Network3D() {
  const { network, incidents, threats, prefs, offline } = useApp()
  const [selected, setSelected] = useState(null)
  const [paused, setPaused] = useState(false)
  const [resetToken, setResetToken] = useState(0)

  const nodes = network?.nodes || []
  const edges = network?.edges || []

  const relatedThreats = useMemo(() => {
    if (!selected) return []
    return threats.filter((t) => t.affected_asset === selected.label || t.destination === selected.id).slice(0, 4)
  }, [selected, threats])

  const relatedIncidents = useMemo(() => {
    if (!selected) return []
    return incidents
      .filter((i) => i.affected_assets?.includes(selected.label) && i.status !== 'RESOLVED')
      .slice(0, 3)
  }, [selected, incidents])

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Digital twin"
        title="3D Cyber Network"
        description="Orbit the simulated infrastructure. Node colour reflects live status from the detection engine; red edges mark active attack paths."
        actions={
          <>
            <button className="btn-ghost text-xs" onClick={() => setPaused((p) => !p)}>
              {paused ? <Play size={14} /> : <Pause size={14} />} {paused ? 'Resume packets' : 'Pause packets'}
            </button>
            <button className="btn-ghost text-xs" onClick={() => setResetToken((t) => t + 1)}>
              <RotateCcw size={14} /> Reset camera
            </button>
          </>
        }
      />

      <div className="grid gap-3 xl:grid-cols-[1fr_320px]">
        <div className="relative h-[440px] overflow-hidden rounded-xl border border-white/[0.08] bg-ink-950 sm:h-[560px]">
          <NetworkScene
            nodes={nodes}
            edges={edges}
            selectedId={selected?.id}
            onSelect={setSelected}
            paused={paused}
            resetToken={resetToken}
            animationIntensity={prefs?.animationIntensity ?? 1}
          />

          <div className="pointer-events-none absolute left-3 top-3 space-y-2">
            <div className="rounded-md border border-white/10 bg-ink-950/80 px-2.5 py-2 backdrop-blur">
              <p className="label-caps mb-1.5">Legend</p>
              <ul className="space-y-1">
                {LEGEND.map(([key, label]) => (
                  <li key={key} className="flex items-center gap-2 text-[11px] text-slate-400">
                    <StatusDot status={key} size={7} />
                    {label}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-white/10 bg-ink-950/80 px-2.5 py-1.5 backdrop-blur">
            <p className="mono text-[10px] uppercase tracking-wider text-slate-500">
              drag = orbit · scroll = zoom · click node = inspect
            </p>
          </div>

          {edges.some((e) => e.status === 'attack') && (
            <div className="pointer-events-none absolute right-3 top-3 flex items-center gap-2 rounded-md border border-alert-500/40 bg-alert-500/10 px-2.5 py-1.5 backdrop-blur">
              <ShieldAlert size={13} className="text-alert-500" />
              <span className="mono text-[10.5px] uppercase tracking-wider text-alert-400">
                Active attack path
              </span>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <Panel title="Node inspector" subtitle="Click any asset in the 3D view">
            {!selected ? (
              <EmptyState
                icon={<Info size={22} />}
                title="No node selected"
                message="Select a node to see status, risk, recent detections and open incidents."
              />
            ) : (
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[15px] font-semibold text-white">{selected.label}</p>
                    <p className="mono text-[11px] uppercase tracking-wider text-slate-500">
                      {selected.type} · {selected.zone} zone
                    </p>
                  </div>
                  <span
                    className="rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
                    style={{
                      color: riskBand(selected.risk).color,
                      borderColor: `${riskBand(selected.risk).color}66`,
                      backgroundColor: `${riskBand(selected.risk).color}15`,
                    }}
                  >
                    {selected.status}
                  </span>
                </div>

                <DefinitionRow label="IP" value={<span className="mono">{selected.ip}</span>} />
                <DefinitionRow label="Risk score" value={<span className="mono">{selected.risk} / 100</span>} />
                <DefinitionRow label="Description" value={<span className="text-xs text-slate-400">{selected.description}</span>} />

                <div>
                  <p className="label-caps mb-1.5">Connections</p>
                  <div className="flex flex-wrap gap-1.5">
                    {edges
                      .filter((e) => e.source === selected.id || e.target === selected.id)
                      .map((e) => {
                        const other = e.source === selected.id ? e.target : e.source
                        const otherNode = nodes.find((n) => n.id === other)
                        return (
                          <span
                            key={`${e.source}-${e.target}`}
                            className="mono rounded border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-slate-400"
                          >
                            {otherNode?.label || other} <span className="text-slate-600">· {e.label}</span>
                          </span>
                        )
                      })}
                  </div>
                </div>

                {relatedThreats.length > 0 && (
                  <div>
                    <p className="label-caps mb-1.5">Recent detections</p>
                    <ul className="space-y-1.5">
                      {relatedThreats.map((t) => (
                        <li key={t.id} className="flex items-center gap-2 text-[11.5px]">
                          <SeverityBadge severity={t.severity} />
                          <span className="truncate text-slate-300">{t.threat_type}</span>
                          <span className="mono ml-auto text-slate-500">{relativeTime(t.timestamp)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {relatedIncidents.length > 0 && (
                  <div>
                    <p className="label-caps mb-1.5">Open incidents</p>
                    <ul className="space-y-1">
                      {relatedIncidents.map((i) => (
                        <li key={i.id} className="text-[11.5px] text-slate-400">
                          <a href={`/app/incidents/${i.id}`} className="hover:text-cyber-300">
                            {i.id} · {i.threat_type}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </Panel>

          <Panel title="Topology facts" subtitle="Static sandbox inventory">
            <div className="space-y-1">
              <DefinitionRow label="Assets" value={nodes.length} />
              <DefinitionRow label="Connections" value={edges.length} />
              <DefinitionRow label="Active attack edges" value={edges.filter((e) => e.status === 'attack').length} />
              <DefinitionRow
                label="Compromised"
                value={nodes.filter((n) => n.status === 'compromised').length}
              />
              <DefinitionRow label="Data source" value={offline ? 'bundled preview' : 'live API'} />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
