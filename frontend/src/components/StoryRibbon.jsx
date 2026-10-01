import React, { useMemo } from 'react'
import { useApp } from '../context/AppContext'

export const STAGES = [
  { key: 'NORMAL', note: 'Baseline telemetry flowing', color: '#2fd98a' },
  { key: 'ANOMALY', note: 'Behaviour deviates from baseline', color: '#f5c518' },
  { key: 'THREAT', note: 'Classified, scored, evidenced', color: '#ff8a3d' },
  { key: 'INVESTIGATION', note: 'AI explains the incident', color: '#38d6f5' },
  { key: 'ATTACK PATH', note: 'Graph reconstructed in 3D', color: '#ff3b5c' },
  { key: 'RESPONSE', note: 'Defensive actions recommended', color: '#8b5cf6' },
  { key: 'CONTAINMENT', note: 'Threat isolated (simulated)', color: '#38d6f5' },
  { key: 'RECOVERY', note: 'Back to a secure state', color: '#2fd98a' },
]

export function useStoryStage() {
  const { incidents, events, dashboard } = useApp()
  return useMemo(() => {
    const active = incidents.filter((i) => i.status === 'OPEN' || i.status === 'INVESTIGATING')
    const contained = incidents.filter((i) => i.status === 'CONTAINED')
    const resolved = incidents.filter((i) => i.status === 'RESOLVED')
    const noisy = events.some((e) => e.severity === 'HIGH' || e.severity === 'CRITICAL')

    if (active.length) {
      const withGraph = active.some((i) => (i.timeline || []).some((t) => t.kind === 'graph'))
      const withAnalysis = active.some((i) => Boolean(i.analysis))
      const withActions = active.some((i) => (i.recommendations || []).length > 0)
      if (!withGraph) return noisy ? 2 : 1
      if (!withAnalysis) return 3
      return withActions ? 5 : 4
    }
    if (contained.length) return 6
    if (resolved.length && (dashboard?.events_analyzed || 0) > 0) return 7
    if (noisy) return 1
    return 0
  }, [incidents, events, dashboard])
}

export default function StoryRibbon({ compact = false }) {
  const stage = useStoryStage()
  return (
    <div className="card overflow-hidden p-0">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
        <div>
          <p className="label-caps">Operational storyline</p>
          <p className="mt-0.5 text-[12px] text-slate-400">
            Current stage:{' '}
            <span className="font-semibold" style={{ color: STAGES[stage].color }}>
              {STAGES[stage].key}
            </span>{' '}
            — {STAGES[stage].note}
          </p>
        </div>
        <span className="mono hidden text-[10px] text-slate-600 sm:block">
          {stage + 1}/{STAGES.length}
        </span>
      </div>
      <ol className={`grid gap-px bg-white/[0.05] ${compact ? 'grid-cols-4 lg:grid-cols-8' : 'grid-cols-2 sm:grid-cols-4 lg:grid-cols-8'}`}>
        {STAGES.map((s, i) => {
          const done = i < stage
          const active = i === stage
          return (
            <li
              key={s.key}
              className="relative bg-ink-900 px-3 py-2.5 transition"
              style={{
                backgroundColor: active ? `${s.color}12` : undefined,
                boxShadow: active ? `inset 0 2px 0 0 ${s.color}` : done ? `inset 0 2px 0 0 ${s.color}55` : undefined,
              }}
              aria-current={active ? 'step' : undefined}
            >
              <span className="mono text-[9.5px] text-slate-600">0{i + 1}</span>
              <p
                className="mt-0.5 text-[10.5px] font-semibold tracking-wide"
                style={{ color: active ? s.color : done ? '#94a3b8' : '#475569' }}
              >
                {s.key}
              </p>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
