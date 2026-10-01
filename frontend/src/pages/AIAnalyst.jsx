import React, { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BrainCircuit, Loader2, Send, Sparkles } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { EmptyState, Panel, SectionHeading, SeverityBadge, StatusPill } from '../components/ui'
import { formatDateTime, riskBand } from '../utils/format'

const QUESTIONS = [
  'What happened?',
  'Why is this dangerous?',
  'What evidence supports this?',
  'Which systems are affected?',
  'What should we do?',
  'What is the attack timeline?',
  'How can we prevent this?',
]

export default function AIAnalyst() {
  const { incidents, actions, offline, pushToast } = useApp()
  const [params, setParams] = useSearchParams()
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)

  const incidentId = params.get('incident') || incidents[0]?.id || ''
  const incident = useMemo(() => incidents.find((i) => i.id === incidentId), [incidents, incidentId])
  const [analysis, setAnalysis] = useState(null)

  useEffect(() => {
    setAnalysis(incident?.analysis || null)
  }, [incident?.id, incident?.analysis])

  const runAnalysis = async (q = question) => {
    if (!incident) return
    setBusy(true)
    const res = await actions.analyze(incident.id, q)
    setBusy(false)
    if (res.ok) {
      setAnalysis(res.data.analysis)
      setQuestion('')
    } else {
      pushToast({ type: 'error', title: 'Analysis unavailable', message: res.error })
    }
  }

  if (!incidents.length) {
    return (
      <div className="space-y-4">
        <SectionHeading
          eyebrow="Investigation"
          title="AI Analyst"
          description="Ask structured questions about an incident and receive an explainable analysis with recommendations."
        />
        <EmptyState
          icon={<BrainCircuit size={26} />}
          title="No incidents to analyse"
          message="Generate one from the simulator — the analyst attaches to the incident record."
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Investigation"
        title="AI Analyst"
        description="Structured explanations generated from the incident record. Uses an external LLM when a key is configured, otherwise the built-in local analysis engine."
        actions={
          <span className="mono rounded border border-white/10 px-2.5 py-1 text-[11px] text-slate-400">
            provider: {analysis?.provider || 'local-analysis-engine'}
          </span>
        }
      />

      <div className="grid gap-3 xl:grid-cols-[300px_1fr]">
        <div className="space-y-3">
          <Panel title="Select incident" subtitle="Cases available for investigation">
            <div className="max-h-[240px] space-y-1.5 overflow-y-auto pr-1">
              {incidents.map((i) => (
                <button
                  key={i.id}
                  onClick={() => setParams({ incident: i.id })}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition ${
                    i.id === incidentId
                      ? 'border-cyber-400/45 bg-cyber-400/[0.08]'
                      : 'border-white/[0.07] hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={i.severity} />
                    <span className="truncate text-[13px] text-slate-200">{i.threat_type}</span>
                  </div>
                  <p className="mono mt-1 text-[10.5px] text-slate-500">
                    {i.id} · risk {i.risk_score} · {i.status}
                  </p>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Ask the analyst" subtitle="Pick a preset or type your own">
            <div className="flex flex-col gap-1.5">
              {QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setQuestion(q)
                    runAnalysis(q)
                  }}
                  disabled={busy || offline}
                  className="rounded-lg border border-white/[0.07] px-3 py-2 text-left text-[12.5px] text-slate-300 transition hover:border-cyber-400/40 hover:text-cyber-300 disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>

            <div className="mt-3 flex gap-2">
              <input
                className="input py-1.5 text-xs"
                placeholder="Custom question…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && question.trim() && runAnalysis()}
                aria-label="Custom analysis question"
              />
              <button
                className="btn-primary px-3"
                onClick={() => runAnalysis()}
                disabled={busy || offline || !question.trim()}
                title={offline ? 'Backend offline' : 'Run analysis'}
              >
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              </button>
            </div>
          </Panel>
        </div>

        <div className="space-y-3">
          {incident && (
            <div className="card flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
              <div>
                <p className="label-caps">Incident</p>
                <p className="mono text-[13px] text-slate-200">{incident.id}</p>
              </div>
              <div>
                <p className="label-caps">Threat</p>
                <p className="text-[13px] text-slate-200">{incident.threat_type}</p>
              </div>
              <div>
                <p className="label-caps">Severity</p>
                <SeverityBadge severity={incident.severity} className="mt-1" />
              </div>
              <div>
                <p className="label-caps">Risk</p>
                <p className="mono text-[13px]" style={{ color: riskBand(incident.risk_score).color }}>
                  {incident.risk_score}/100
                </p>
              </div>
              <div>
                <p className="label-caps">Status</p>
                <StatusPill status={incident.status} className="mt-1" />
              </div>
              <div>
                <p className="label-caps">First seen</p>
                <p className="mono text-[12.5px] text-slate-300">{formatDateTime(incident.first_seen)}</p>
              </div>
            </div>
          )}

          {!analysis ? (
            <EmptyState
              icon={<Sparkles size={24} />}
              title="No analysis generated yet"
              message="Choose a question on the left to have the AI analyst explain this incident."
              action={
                <button className="btn-primary text-xs" onClick={() => runAnalysis('What happened?')} disabled={busy || offline}>
                  {busy ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />} Analyse incident
                </button>
              }
            />
          ) : (
            <>
              <div className="card border-cyber-400/20 p-4">
                <div className="flex items-center gap-2">
                  <Sparkles size={15} className="text-cyber-400" />
                  <p className="label-caps text-cyber-300">Executive summary</p>
                </div>
                <p className="mt-2 text-[14px] leading-relaxed text-slate-200">{analysis.summary}</p>
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                {analysis.sections.map((s, i) => (
                  <Panel key={`${s.heading}-${i}`} title={s.heading}>
                    <p className="whitespace-pre-line text-[13px] leading-relaxed text-slate-300">{s.body}</p>
                  </Panel>
                ))}
              </div>

              <Panel
                title="Recommended defensive actions"
                subtitle="Simulation-only recommendations — no action is taken against real systems"
              >
                <ol className="space-y-2">
                  {analysis.recommendations.map((r, i) => (
                    <li key={i} className="flex gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5">
                      <span className="mono text-[12px] text-cyber-400">{String(i + 1).padStart(2, '0')}</span>
                      <div className="min-w-0">
                        <p className="text-[13.5px] font-medium text-slate-100">
                          {r.title}
                          <span className="mono ml-2 text-[10px] uppercase tracking-wider text-slate-500">{r.priority}</span>
                        </p>
                        <p className="mt-0.5 text-[12.5px] leading-relaxed text-slate-400">{r.detail}</p>
                      </div>
                    </li>
                  ))}
                </ol>
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
