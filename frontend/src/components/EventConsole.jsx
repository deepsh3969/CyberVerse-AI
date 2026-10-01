import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Pause, Play, Radio, Trash2 } from 'lucide-react'
import { formatTime } from '../utils/format'
import { EmptyState, ToolbarButton } from './ui'

const SEV_COLOR = {
  CRITICAL: 'text-alert-500',
  HIGH: 'text-orange-400',
  MEDIUM: 'text-warn-400',
  LOW: 'text-ok-400',
  INFO: 'text-slate-400',
}

export default function EventConsole({ events = [], title = 'Live Event Stream', height = 320, showFilters = true }) {
  const [paused, setPaused] = useState(false)
  const [query, setQuery] = useState('')
  const [type, setType] = useState('ALL')
  const scroller = useRef(null)
  const snapshot = useRef(events)

  if (!paused) snapshot.current = events

  const types = useMemo(() => {
    const set = new Set(events.map((e) => e.event_type))
    return ['ALL', ...Array.from(set).slice(0, 12)]
  }, [events])

  const visible = useMemo(() => {
    const list = paused ? snapshot.current : events
    const q = query.trim().toLowerCase()
    return list.filter((e) => {
      if (type !== 'ALL' && e.event_type !== type) return false
      if (!q) return true
      return `${e.event_type} ${e.source} ${e.destination} ${e.message}`.toLowerCase().includes(q)
    })
  }, [events, paused, query, type])

  useEffect(() => {
    if (!paused && scroller.current) scroller.current.scrollTop = 0
  }, [events, paused])

  return (
    <div className="card flex flex-col overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Radio size={14} className="text-ok-400 animate-pulseDot" />
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          <span className="mono text-[11px] text-slate-500">{visible.length} shown</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            className={`btn px-2.5 py-1 text-xs ${paused ? 'border-warn-500/40 text-warn-400' : 'border-white/10 text-slate-300'}`}
            title={paused ? 'Resume stream' : 'Pause stream'}
          >
            {paused ? <Play size={13} /> : <Pause size={13} />}
            {paused ? 'Paused' : 'Live'}
          </button>
          <button
            type="button"
            onClick={() => {
              setQuery('')
              setType('ALL')
            }}
            className="btn border border-white/10 px-2.5 py-1 text-xs text-slate-400 hover:text-cyber-300"
            title="Clear filters"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </header>

      {showFilters && (
        <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.05] px-4 py-2">
          <input
            className="input max-w-[220px] py-1 text-xs"
            placeholder="Filter events…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Filter events"
          />
          <div className="flex flex-wrap gap-1">
            {types.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setType(t)}
                className={`mono rounded px-1.5 py-0.5 text-[10px] transition ${
                  type === t ? 'bg-cyber-500/20 text-cyber-300' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      )}

      <div
        ref={scroller}
        className="mono flex-1 overflow-y-auto px-3 py-2 text-[11.5px] leading-[1.7]"
        style={{ height }}
      >
        {visible.length === 0 ? (
          <div className="p-3">
            <EmptyState title="No events match" message="Run a simulation to generate telemetry." />
          </div>
        ) : (
          visible.map((e) => (
            <div key={e.id} className="flex gap-3 border-b border-white/[0.03] py-1 last:border-0">
              <span className="shrink-0 text-slate-600">{formatTime(e.timestamp)}</span>
              <span className={`w-[168px] shrink-0 truncate ${SEV_COLOR[e.severity] || 'text-slate-400'}`}>
                {e.event_type}
              </span>
              <span className="hidden w-[120px] shrink-0 truncate text-slate-500 sm:block">{e.source}</span>
              <span className="hidden w-[110px] shrink-0 truncate text-cyber-600 md:block">{e.destination}</span>
              <span className="min-w-0 flex-1 truncate text-slate-400">{e.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
