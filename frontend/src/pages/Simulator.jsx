import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FlaskConical, GitBranch, Loader2, Play, ShieldAlert } from 'lucide-react'
import { useApp } from '../context/AppContext'
import EventConsole from '../components/EventConsole'
import { EmptyState, Panel, SectionHeading, SeverityBadge, StatusPill } from '../components/ui'
import { formatTime, riskBand, severityBgClass, severityClass } from '../utils/format'

const INTENSITIES = [
  { key: 'low', label: 'Low', note: 'Shorter event sequence' },
  { key: 'normal', label: 'Normal', note: 'Realistic volume' },
  { key: 'high', label: 'High', note: 'Longer, noisier burst' },
]

const SEV_TONE = {
  MEDIUM: 'text-warn-400',
  HIGH: 'text-orange-400',
  CRITICAL: 'text-alert-500',
}

export default function Simulator() {
  const { scenarios, events, actions, offline, pushToast } = useApp()
  const navigate = useNavigate()
  const [intensity, setIntensity] = useState('normal')
  const [busy, setBusy] = useState(null)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])

  const run = async (scenario) => {
    if (busy) return
    setBusy(scenario.key)
    const res = await actions.simulate(scenario.key, { intensity })
    setBusy(null)
    if (!res.ok) {
      pushToast({ type: 'error', title: 'Simulation failed', message: res.error })
      return
    }
    const data = res.data
    setResult({ ...data, key: scenario.key, at: Date.now() })
    setHistory((h) => [
      {
        key: scenario.key,
        name: data.scenario,
        at: Date.now(),
        threats: data.threats.length,
        incident: data.incident?.id,
        risk: data.incident?.risk_score,
      },
      ...h,
    ].slice(0, 8))
  }

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Safe simulation"
        title="Attack Simulator"
        description="Generates synthetic security events inside this sandbox and feeds them straight into the detection pipeline. No real traffic, hosts or credentials are involved."
        actions={
          <div className="flex items-center gap-1.5">
            {INTENSITIES.map((i) => (
              <button
                key={i.key}
                onClick={() => setIntensity(i.key)}
                title={i.note}
                className={`rounded-md border px-3 py-1.5 text-[11.5px] transition ${
                  intensity === i.key
                    ? 'border-cyber-400/45 bg-cyber-400/10 text-cyber-300'
                    : 'border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                {i.label}
              </button>
            ))}
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {scenarios.map((s) => (
          <article key={s.key} className="card card-hover flex flex-col p-4">
            <div className="flex items-start justify-between gap-2">
              <span className={`grid h-8 w-8 place-items-center rounded-lg border ${severityBgClass(s.severity)} ${severityClass(s.severity)}`}>
                <FlaskConical size={15} />
              </span>
              <span className={`mono text-[10px] uppercase tracking-wider ${SEV_TONE[s.severity] || 'text-slate-400'}`}>
                {s.severity}
              </span>
            </div>
            <h3 className="mt-3 text-[14px] font-semibold text-white">{s.name}</h3>
            <p className="mt-1 flex-1 text-[12px] leading-relaxed text-slate-400">{s.description}</p>
            <button
              className="btn-primary mt-3 w-full py-2 text-xs"
              onClick={() => run(s)}
              disabled={Boolean(busy) || offline}
              title={offline ? 'Backend offline' : 'Generate synthetic events'}
            >
              {busy === s.key ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {busy === s.key ? 'Running…' : 'Simulate Attack'}
            </button>
          </article>
        ))}
      </div>

      {result && (
        <div className="grid gap-3 xl:grid-cols-[1fr_340px]">
          <Panel
            title={`Result · ${result.scenario}`}
            subtitle={`${result.events.length} events generated · ${result.threats.length} threat(s) classified`}
            action={
              result.incident ? (
                <div className="flex gap-2">
                  <button className="btn-ghost px-2.5 py-1 text-[11.5px]" onClick={() => navigate(`/app/incidents/${result.incident.id}`)}>
                    <ShieldAlert size={13} /> Incident
                  </button>
                  <button className="btn-ghost px-2.5 py-1 text-[11.5px]" onClick={() => navigate(`/app/attack-graph?incident=${result.incident.id}`)}>
                    <GitBranch size={13} /> Attack graph
                  </button>
                </div>
              ) : null
            }
          >
            {result.threats.map((t) => (
              <div key={t.id} className="mb-3 rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={t.severity} />
                  <span className="text-[14px] font-semibold text-white">{t.threat_type}</span>
                  <span className="mono ml-auto text-[12px]" style={{ color: riskBand(t.risk_score).color }}>
                    risk {t.risk_score} · confidence {(t.confidence * 100).toFixed(0)}% · anomaly {Number(t.anomaly_score).toFixed(2)}
                  </span>
                </div>
                <p className="mono mt-1 text-[11.5px] text-slate-500">
                  {t.source} → {t.affected_asset} · {t.detector}
                </p>
                <ul className="mt-2 space-y-1">
                  {t.evidence.map((e, i) => (
                    <li key={i} className="flex gap-2 text-[12.5px] text-slate-400">
                      <span className="text-cyber-600">▸</span>
                      {e}
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            {result.incident && (
              <div className="rounded-lg border border-alert-500/25 bg-alert-500/[0.05] p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[12px] text-alert-400">{result.incident.id}</span>
                  <StatusPill status={result.incident.status} />
                  <span className="mono ml-auto text-[11.5px] text-slate-400">
                    {result.incident.affected_assets.join(', ')}
                  </span>
                </div>
                <p className="mt-2 text-[12.5px] text-slate-300">{result.message}</p>
                {result.attack_graph && (
                  <p className="mono mt-2 text-[11.5px] text-cyber-300">
                    {result.attack_graph.path_labels.join('  →  ')}
                  </p>
                )}
              </div>
            )}

            <div className="mt-3">
              <p className="label-caps mb-1.5">Generated event sequence</p>
              <div className="mono max-h-44 space-y-0.5 overflow-y-auto rounded-lg border border-white/[0.06] bg-ink-950/60 p-2.5 text-[11.5px]">
                {result.events.map((e) => (
                  <div key={e.id} className="flex gap-3">
                    <span className="text-slate-600">{formatTime(e.timestamp)}</span>
                    <span className={`${severityClass(e.severity)} w-[170px] shrink-0 truncate`}>{e.event_type}</span>
                    <span className="min-w-0 truncate text-slate-500">{e.message}</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <div className="space-y-3">
            <Panel title="Run history" subtitle="This session">
              {history.length === 0 ? (
                <EmptyState title="No runs yet" />
              ) : (
                <ul className="space-y-1.5">
                  {history.map((h, i) => (
                    <li key={`${h.key}-${h.at}`} className="flex items-center gap-2 text-[12px]">
                      <span className="truncate text-slate-300">{h.name}</span>
                      <span className="mono ml-auto text-slate-500">{formatTime(h.at / 1000)}</span>
                      <span className="mono text-cyber-400">{h.threats}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
            <Panel title="Detection pipeline">
              <ol className="space-y-2 text-[12.5px] text-slate-400">
                {[
                  'Synthetic events generated',
                  'Feature vector extracted per event',
                  'Isolation Forest anomaly score',
                  'Rule engine correlation',
                  'Threat classification + risk score',
                  'Incident + attack graph created',
                ].map((step, i) => (
                  <li key={step} className="flex gap-2.5">
                    <span className="mono text-cyber-500">{i + 1}</span>
                    {step}
                  </li>
                ))}
              </ol>
            </Panel>
          </div>
        </div>
      )}

      <EventConsole events={events} title="Sandbox event stream" height={260} />
    </div>
  )
}
