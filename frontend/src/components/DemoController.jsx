import React from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, CircleDashed, PlayCircle, RotateCcw, ShieldAlert, Square } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { ProgressBar } from './ui'

const STATE_LABEL = {
  idle: 'Ready',
  running: 'Running',
  timeout: 'Awaiting containment',
  complete: 'Complete',
  failed: 'Failed',
  aborted: 'Stopped',
  busy: 'Busy',
}

export function DemoCompact() {
  const { demo, actions, offline, prefs } = useApp()
  const navigate = useNavigate()
  const state = demo?.state || 'idle'
  const pct = state === 'idle' ? 0 : ((Number(demo.step) + 1) / (demo.steps?.length || 12)) * 100

  if (!prefs?.demoMode) return null

  if (state === 'running' || state === 'timeout') {
    return (
      <div className="hidden w-52 items-center gap-2 md:flex" title={demo.detail}>
        <span className="h-2 w-2 shrink-0 animate-pulseDot rounded-full bg-warn-400" />
        <div className="min-w-0 flex-1">
          <ProgressBar value={pct} color="#f5c524" height={5} />
          <p className="mt-0.5 truncate text-[10.5px] text-slate-400">{demo.label}</p>
        </div>
        <button className="text-slate-500 hover:text-alert-400" onClick={actions.stopDemo} aria-label="Stop demo">
          <Square size={13} />
        </button>
      </div>
    )
  }

  return (
    <button
      className="btn-ghost hidden px-3 py-1.5 text-xs md:inline-flex"
      onClick={async () => {
        if (offline) return
        if (state === 'complete' || state === 'failed' || state === 'aborted') await actions.resetDemo()
        await actions.startDemo()
        navigate('/app')
      }}
      disabled={offline}
      title={offline ? 'Backend offline - demo unavailable' : 'Run the 2 minute scripted scenario'}
    >
      <PlayCircle size={14} className="text-cyber-400" />
      Hackathon Demo
    </button>
  )
}

export default function DemoController() {
  const { demo, actions, offline } = useApp()
  const navigate = useNavigate()
  const state = demo?.state || 'idle'
  const steps = demo?.steps || []
  const current = Number(demo?.step ?? -1)
  const pct = state === 'idle' ? 0 : ((current + 1) / (steps.length || 12)) * 100

  const start = async () => {
    if (state === 'complete' || state === 'failed' || state === 'aborted') await actions.resetDemo()
    await actions.startDemo()
  }

  return (
    <div className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="label-caps">Scripted walkthrough</p>
          <h3 className="mt-1 text-sm font-semibold text-white">Hackathon Demo</h3>
          <p className="mt-1 max-w-md text-xs text-slate-400">
            A repeatable 2 minute narrative: normal traffic → anomaly → AI detection → attack path →
            investigation → containment → recovery.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {state === 'running' && (
            <button className="btn-ghost text-xs" onClick={actions.stopDemo}>
              <Square size={13} /> Stop
            </button>
          )}
          {(state === 'timeout' || state === 'complete') && (
            <button className="btn-ghost text-xs" onClick={actions.resetDemo}>
              <RotateCcw size={13} /> Reset
            </button>
          )}
          {state === 'timeout' && demo?.incident_id && (
            <button
              className="btn-danger text-xs"
              onClick={() => navigate(`/app/incidents/${demo.incident_id}`)}
            >
              <ShieldAlert size={13} /> Open incident
            </button>
          )}
          {state !== 'running' && state !== 'timeout' && (
            <button className="btn-primary text-xs" onClick={start} disabled={offline}>
              <PlayCircle size={14} /> {state === 'idle' ? 'Start Hackathon Demo' : 'Run Again'}
            </button>
          )}
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-1.5 flex items-center justify-between text-[11px] text-slate-400">
          <span className="mono">
            {STATE_LABEL[state] || state}
            {state === 'running' ? ` · step ${current + 1}/${steps.length}` : ''}
          </span>
          <span className="mono">{Math.round(pct)}%</span>
        </div>
        <ProgressBar value={pct} color={state === 'complete' ? '#2fd98a' : '#38d6f5'} height={6} />
        {state !== 'idle' && demo?.label && (
          <p className="mt-2 text-xs text-slate-300">
            <span className="font-medium text-cyber-300">{demo.label}</span>
            {demo.detail ? ` — ${demo.detail}` : ''}
          </p>
        )}
      </div>

      <ol className="mt-4 grid gap-1.5 sm:grid-cols-2">
        {steps.map((s, idx) => {
          const done = state === 'complete' || idx < current
          const active = idx === current
          return (
            <li
              key={s.index}
              className={`flex items-start gap-2 rounded-md border px-2 py-1.5 text-[11.5px] transition ${
                active
                  ? 'border-cyber-400/40 bg-cyber-400/[0.07] text-slate-100'
                  : done
                    ? 'border-ok-400/20 bg-ok-400/[0.04] text-slate-400'
                    : 'border-white/[0.05] text-slate-500'
              }`}
            >
              {done ? (
                <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-ok-400" />
              ) : (
                <CircleDashed size={13} className={`mt-0.5 shrink-0 ${active ? 'text-cyber-400' : 'text-slate-600'}`} />
              )}
              <span className="leading-snug">{s.label}</span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
