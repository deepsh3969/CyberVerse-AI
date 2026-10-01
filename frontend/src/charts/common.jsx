import React from 'react'

export const AXIS = {
  stroke: '#334155',
  tick: { fill: '#64748b', fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
  tickLine: false,
}

export const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#0a101c',
    border: '1px solid rgba(255,255,255,0.12)',
    borderRadius: 8,
    fontSize: 12,
    fontFamily: 'Inter, sans-serif',
    color: '#e2e8f0',
    boxShadow: '0 12px 30px -14px rgba(0,0,0,0.9)',
  },
  labelStyle: { color: '#94a3b8', fontSize: 11, marginBottom: 4 },
  cursor: { fill: 'rgba(56,214,245,0.06)' },
}

export const GRID = {
  stroke: 'rgba(148,163,184,0.08)',
  strokeDasharray: '3 3',
}

export const formatAxisTime = (t) => {
  const d = new Date(Number(t) * (Number(t) > 1e12 ? 1 : 1000))
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export function ChartFrame({ title, subtitle, action, children, height = 210 }) {
  return (
    <div className="card flex flex-col">
      <header className="flex items-start justify-between gap-3 px-4 py-3">
        <div>
          <h3 className="text-[13px] font-semibold text-slate-100">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </header>
      <div className="px-2 pb-3" style={{ height }}>
        {children}
      </div>
    </div>
  )
}
