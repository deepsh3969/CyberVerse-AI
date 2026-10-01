import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BrainCircuit, Filter, Search, X } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { EmptyState, Panel, SectionHeading, SeverityBadge, ToolbarButton } from '../components/ui'
import { formatDateTime, relativeTime, riskBand } from '../utils/format'

const SEVERITIES = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

export default function Threats() {
  const { threats, incidents, actions, offline } = useApp()
  const navigate = useNavigate()
  const [severity, setSeverity] = useState('ALL')
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return threats.filter((t) => {
      if (severity !== 'ALL' && t.severity !== severity) return false
      if (!q) return true
      return `${t.threat_type} ${t.source} ${t.affected_asset} ${(t.evidence || []).join(' ')}`
        .toLowerCase()
        .includes(q)
    })
  }, [threats, severity, query])

  const incidentFor = (threatId) => incidents.find((i) => (i.threat_ids || []).includes(threatId))

  const analyze = async (threat) => {
    const inc = incidentFor(threat.id)
    if (!inc) {
      navigate('/app/incidents')
      return
    }
    navigate(`/app/ai-analyst?incident=${inc.id}`)
  }

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Detection output"
        title="Threats"
        description="Every classification produced by the hybrid Isolation Forest + rule engine, with confidence and supporting evidence."
        actions={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                className="input w-52 py-1.5 pl-8 text-xs"
                placeholder="Search threats…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search threats"
              />
            </div>
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-1.5">
        <Filter size={13} className="mr-1 text-slate-500" />
        {SEVERITIES.map((s) => (
          <button
            key={s}
            onClick={() => setSeverity(s)}
            className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition ${
              severity === s
                ? 'border-cyber-400/40 bg-cyber-400/10 text-cyber-300'
                : 'border-white/10 text-slate-400 hover:text-slate-200'
            }`}
          >
            {s}
          </button>
        ))}
        <span className="mono ml-auto text-[11px] text-slate-500">{filtered.length} of {threats.length}</span>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No threats match the current filter"
          message={offline ? 'Backend offline — start the API to load detections.' : 'Run a simulation to generate detections.'}
          action={
            <button className="btn-primary text-xs" onClick={() => navigate('/app/simulator')}>
              Open simulator
            </button>
          }
        />
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {filtered.map((t) => {
            const inc = incidentFor(t.id)
            const band = riskBand(t.risk_score)
            return (
              <article key={t.id} className="card card-hover p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={t.severity} />
                      <h3 className="text-[15px] font-semibold text-white">{t.threat_type}</h3>
                      <span className="mono text-[10.5px] text-slate-600">{t.id}</span>
                    </div>
                    <p className="mono mt-1 text-[11.5px] text-slate-500">
                      {t.source} → {t.affected_asset} · {formatDateTime(t.timestamp)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="mono text-xl font-semibold" style={{ color: band.color }}>
                      {t.risk_score}
                    </p>
                    <p className="mono text-[10px] uppercase tracking-wider text-slate-500">risk</p>
                  </div>
                </div>

                <ul className="mt-3 space-y-1">
                  {(t.evidence || []).slice(0, 3).map((e, i) => (
                    <li key={i} className="flex gap-2 text-[12px] leading-relaxed text-slate-400">
                      <span className="text-cyber-600">▸</span>
                      {e}
                    </li>
                  ))}
                </ul>

                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/[0.06] pt-3">
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span className="mono">confidence {(t.confidence * 100).toFixed(0)}%</span>
                    <span className="text-slate-700">·</span>
                    <span className="mono">anomaly {Number(t.anomaly_score).toFixed(2)}</span>
                    <span className="text-slate-700">·</span>
                    <span className="mono">{t.detector}</span>
                  </div>
                  <div className="ml-auto flex gap-2">
                    <button className="btn-ghost px-2.5 py-1 text-[11.5px]" onClick={() => setSelected(t)}>
                      Details
                    </button>
                    <button
                      className="btn-ghost px-2.5 py-1 text-[11.5px]"
                      onClick={() => analyze(t)}
                      disabled={offline}
                      title={offline ? 'Backend offline' : 'Open in AI Analyst'}
                    >
                      <BrainCircuit size={13} /> Analyze
                    </button>
                    {inc && (
                      <button className="btn-ghost px-2.5 py-1 text-[11.5px]" onClick={() => navigate(`/app/incidents/${inc.id}`)}>
                        Incident
                      </button>
                    )}
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 no-print" role="dialog" aria-modal="true">
          <div className="card max-h-[85vh] w-full max-w-2xl overflow-y-auto p-0">
            <header className="flex items-start justify-between gap-3 border-b border-white/[0.07] px-5 py-4">
              <div>
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={selected.severity} />
                  <h3 className="text-lg font-semibold text-white">{selected.threat_type}</h3>
                </div>
                <p className="mono mt-1 text-[11.5px] text-slate-500">{selected.id}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-white" aria-label="Close">
                <X size={18} />
              </button>
            </header>
            <div className="space-y-4 px-5 py-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {[
                  ['Severity', selected.severity],
                  ['Risk', `${selected.risk_score}/100`],
                  ['Confidence', `${(selected.confidence * 100).toFixed(0)}%`],
                  ['Anomaly', Number(selected.anomaly_score).toFixed(2)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-2.5">
                    <p className="label-caps">{k}</p>
                    <p className="mono mt-1 text-sm text-white">{v}</p>
                  </div>
                ))}
              </div>

              <div>
                <p className="label-caps mb-2">Evidence</p>
                <ul className="space-y-1.5">
                  {(selected.evidence || []).map((e, i) => (
                    <li key={i} className="rounded border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-[13px] text-slate-300">
                      {e}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-white/[0.07] p-3">
                  <p className="label-caps mb-1">Source</p>
                  <p className="mono text-[13px] text-slate-200">{selected.source}</p>
                </div>
                <div className="rounded-lg border border-white/[0.07] p-3">
                  <p className="label-caps mb-1">Affected asset</p>
                  <p className="mono text-[13px] text-slate-200">{selected.affected_asset}</p>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button className="btn-ghost text-xs" onClick={() => setSelected(null)}>
                  Close
                </button>
                <ToolbarButton variant="primary" icon={BrainCircuit} onClick={() => analyze(selected)}>
                  Open in AI Analyst
                </ToolbarButton>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
