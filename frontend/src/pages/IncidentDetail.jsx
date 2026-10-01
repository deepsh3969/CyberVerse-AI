import React, { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  FileText,
  GitBranch,
  Loader2,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import {
  DefinitionRow,
  EmptyState,
  Panel,
  SectionHeading,
  SeverityBadge,
  Spinner,
  StatusPill,
} from '../components/ui'
import { formatDateTime, formatTime, riskBand } from '../utils/format'

function Timeline({ items }) {
  const sorted = [...(items || [])].sort((a, b) => a.time - b.time)
  const tone = (kind) => {
    if (kind === 'contain') return '#38d6f5'
    if (kind === 'detect' || kind === 'graph') return '#ff3b5c'
    if (kind === 'status') return '#f5c518'
    return '#475569'
  }
  return (
    <ol className="relative ml-1 border-l border-white/[0.09] pl-4">
      {sorted.map((t, i) => (
        <li key={i} className="relative pb-4 last:pb-0">
          <span
            className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-ink-900"
            style={{ backgroundColor: tone(t.kind) }}
          />
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="mono text-[11px] text-slate-500">{formatTime(t.time)}</span>
            <span className="mono text-[10.5px] uppercase tracking-wider" style={{ color: tone(t.kind) }}>
              {t.kind}
            </span>
          </div>
          <p className="text-[13px] text-slate-200">{t.label}</p>
          {t.detail && <p className="mono text-[11.5px] text-slate-500">{t.detail}</p>}
        </li>
      ))}
    </ol>
  )
}

export default function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { incidents, actions, offline, pushToast } = useApp()
  const { canWrite } = useAuth()
  const [analysing, setAnalysing] = useState(false)
  const [containing, setContaining] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const incident = useMemo(() => incidents.find((i) => i.id === id), [incidents, id])

  if (!incident) {
    return (
      <div className="space-y-4">
        <SectionHeading eyebrow="Case" title="Incident not found" />
        <EmptyState
          icon={<ShieldAlert size={26} />}
          title={offline ? 'Backend offline' : 'This incident does not exist'}
          message={offline ? 'Live incident data requires the API. Start the backend and retry.' : 'It may have been removed by a sandbox reset.'}
          action={
            <Link to="/app/incidents" className="btn-primary text-xs">
              Back to incidents
            </Link>
          }
        />
      </div>
    )
  }

  const contained = incident.status === 'CONTAINED' || incident.status === 'RESOLVED'
  const band = riskBand(incident.risk_score)

  const doContain = async () => {
    setContaining(true)
    const res = await actions.contain(incident.id)
    setContaining(false)
    setConfirming(false)
    if (!res.ok) pushToast({ type: 'error', title: 'Containment failed', message: res.error })
  }

  const doAnalyse = async (question = '') => {
    setAnalysing(true)
    const res = await actions.analyze(incident.id, question)
    setAnalysing(false)
    if (!res.ok) pushToast({ type: 'error', title: 'Analysis failed', message: res.error })
  }

  const analysis = incident.analysis

  return (
    <div className="space-y-4">
      <button className="flex items-center gap-1.5 text-[12.5px] text-slate-400 hover:text-cyber-300" onClick={() => navigate('/app/incidents')}>
        <ArrowLeft size={14} /> All incidents
      </button>

      <SectionHeading
        eyebrow={`Case ${incident.id}`}
        title={`${incident.threat_type} — ${incident.affected_assets?.join(', ')}`}
        description={`First seen ${formatDateTime(incident.first_seen)} · last seen ${formatDateTime(incident.last_seen)} · source ${incident.source}`}
        actions={
          <>
            <Link to={`/app/ai-analyst?incident=${incident.id}`} className="btn-ghost text-xs">
              <BrainCircuit size={14} /> AI Analyst
            </Link>
            <Link to={`/app/attack-graph?incident=${incident.id}`} className="btn-ghost text-xs">
              <GitBranch size={14} /> Attack graph
            </Link>
            <Link to={`/app/reports/${incident.id}`} className="btn-ghost text-xs">
              <FileText size={14} /> Report
            </Link>
            {!contained && (
              <button
                className="btn-danger text-xs"
                onClick={() => setConfirming(true)}
                disabled={offline || containing || !canWrite}
                title={canWrite ? undefined : 'Analyst role required'}
              >
                <ShieldCheck size={14} /> Contain threat
              </button>
            )}
          </>
        }
      />

      {/* containment banner */}
      {contained && incident.containment && (
        <div className="animate-slideUp rounded-xl border border-cyber-400/35 bg-cyber-400/[0.07] p-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={17} className="text-cyber-400" />
            <p className="text-[15px] font-semibold text-cyber-300">THREAT CONTAINED</p>
            <span className="mono ml-auto text-[11px] text-slate-500">
              {formatDateTime(incident.containment.at)} · {incident.containment.by} · mode: {incident.containment.mode}
            </span>
          </div>
          <ul className="mt-3 grid gap-1.5 sm:grid-cols-2">
            {(incident.containment.actions || []).map((a) => (
              <li key={a} className="flex items-center gap-2 text-[13px] text-slate-300">
                <CheckCircle2 size={13} className="text-ok-400" /> {a}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[11.5px] text-slate-500">
            All containment actions above are simulated inside the CyberVerse sandbox.
          </p>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        {/* left column */}
        <div className="space-y-3 lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ['Severity', incident.severity, incident.severity],
              ['Risk score', `${incident.risk_score}/100`, null],
              ['Confidence', `${Math.round(Math.min(0.99, 0.8 + incident.risk_score / 500) * 100)}%`, null],
              ['Status', incident.status, null],
            ].map(([label, value], idx) => (
              <div key={label} className="card p-3">
                <p className="label-caps">{label}</p>
                <p
                  className="mono mt-1.5 text-lg font-semibold"
                  style={
                    idx === 1
                      ? { color: band.color }
                      : idx === 3
                        ? { color: contained ? '#38d6f5' : '#ff8a3d' }
                        : undefined
                  }
                >
                  {value}
                </p>
                {idx === 0 && <div className="mt-1"><SeverityBadge severity={incident.severity} /></div>}
                {idx === 3 && <div className="mt-1"><StatusPill status={incident.status} /></div>}
              </div>
            ))}
          </div>

          <Panel title="Evidence" subtitle="Signals that justified the classification">
            <ul className="space-y-2">
              {(incident.evidence || []).map((e, i) => (
                <li key={i} className="flex gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-[13px] text-slate-300">
                  <span className="mono text-cyber-500">{String(i + 1).padStart(2, '0')}</span>
                  {e}
                </li>
              ))}
              {!incident.evidence?.length && <EmptyState title="No evidence attached" />}
            </ul>
          </Panel>

          <Panel
            title="AI analysis"
            subtitle={analysis ? `Generated by ${analysis.provider}` : 'Not generated yet'}
            action={
              <button
                className="btn-ghost px-2.5 py-1 text-[11.5px]"
                onClick={() => doAnalyse()}
                disabled={analysing || offline || !canWrite}
                title={canWrite ? undefined : 'Analyst role required'}
              >
                {analysing ? <Loader2 size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
                {analysis ? 'Regenerate' : 'Analyse'}
              </button>
            }
          >
            {!analysis ? (
              <EmptyState
                title="Awaiting analysis"
                message="Generate a structured explanation of what happened, why it matters and what to do next."
              />
            ) : (
              <div className="space-y-3">
                <p className="text-[13.5px] leading-relaxed text-slate-200">{analysis.summary}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  {analysis.sections.map((s, i) => (
                    <div key={i} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
                      <p className="label-caps mb-1">{s.heading}</p>
                      <p className="whitespace-pre-line text-[12.5px] leading-relaxed text-slate-400">{s.body}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Panel>

          <Panel title="Attack timeline" subtitle={`${incident.timeline?.length || 0} recorded events`}>
            <Timeline items={incident.timeline} />
          </Panel>
        </div>

        {/* right column */}
        <div className="space-y-3">
          <Panel title="Case facts">
            <div className="space-y-0.5">
              <DefinitionRow label="Incident ID" value={<span className="mono">{incident.id}</span>} />
              <DefinitionRow label="Threat type" value={incident.threat_type} />
              <DefinitionRow label="Status" value={<StatusPill status={incident.status} />} />
              <DefinitionRow label="Source" value={<span className="mono">{incident.source}</span>} />
              <DefinitionRow label="Destination" value={<span className="mono">{incident.destination || '—'}</span>} />
              <DefinitionRow label="First seen" value={<span className="mono">{formatDateTime(incident.first_seen)}</span>} />
              <DefinitionRow label="Last seen" value={<span className="mono">{formatDateTime(incident.last_seen)}</span>} />
              <DefinitionRow label="Affected assets" value={incident.affected_assets?.join(', ')} />
              <DefinitionRow label="Threat IDs" value={<span className="mono text-xs">{incident.threat_ids?.join(', ')}</span>} />
            </div>
          </Panel>

          <Panel title="Recommended actions" subtitle="Contextual defensive playbook (simulation only)">
            <ol className="space-y-2">
              {(incident.recommendations || []).map((r, i) => (
                <li key={i} className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                  <p className="text-[13px] font-medium text-slate-100">
                    <span className="mono mr-1.5 text-cyber-500">{i + 1}</span>
                    {r.title}
                    <span className="mono ml-2 text-[10px] uppercase tracking-wider text-slate-500">{r.priority}</span>
                  </p>
                  <p className="mt-1 text-[12.5px] leading-relaxed text-slate-400">{r.detail}</p>
                </li>
              ))}
              {!incident.recommendations?.length && <EmptyState title="No recommendations" />}
            </ol>

            {!contained && (
              <button
                className="btn-danger mt-3 w-full text-xs"
                onClick={() => setConfirming(true)}
                disabled={offline || containing || !canWrite}
                title={canWrite ? undefined : 'Analyst role required'}
              >
                {containing ? <Spinner size={14} /> : <ShieldCheck size={14} />} Contain threat
              </button>
            )}
          </Panel>

          <Panel title="Next steps">
            <div className="flex flex-col gap-2">
              <Link to={`/app/reports/${incident.id}`} className="btn-ghost w-full text-xs">
                <ScrollText size={14} /> Generate report
              </Link>
              <Link to="/app/network" className="btn-ghost w-full text-xs">
                <GitBranch size={14} /> Inspect 3D network
              </Link>
            </div>
          </Panel>
        </div>
      </div>

      {/* confirmation modal */}
      {confirming && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 no-print" role="dialog" aria-modal="true">
          <div className="card w-full max-w-md p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck size={18} className="text-cyber-400" />
              <h3 className="text-[16px] font-semibold text-white">Confirm containment</h3>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-slate-400">
              This runs the simulated containment playbook for <span className="mono text-slate-200">{incident.id}</span>:
            </p>
            <ul className="mt-3 space-y-1.5 text-[12.5px] text-slate-300">
              <li>✓ Endpoint isolated</li>
              <li>✓ Suspicious session terminated</li>
              <li>✓ Threat path blocked</li>
              <li>✓ Monitoring increased</li>
            </ul>
            <p className="mt-3 text-[11.5px] text-warn-400">
              No real systems are touched — these actions only change state inside the sandbox.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button className="btn-ghost text-xs" onClick={() => setConfirming(false)}>
                Cancel
              </button>
              <button className="btn-danger text-xs" onClick={doContain} disabled={containing}>
                {containing ? <Spinner size={14} /> : <ShieldCheck size={14} />} Contain now
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
