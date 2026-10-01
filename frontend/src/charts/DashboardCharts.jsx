import React, { useMemo } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { AXIS, formatAxisTime, GRID, TOOLTIP_STYLE } from './common'

const SEV_COLORS = { LOW: '#2fd98a', MEDIUM: '#f5c518', HIGH: '#ff8a3d', CRITICAL: '#ff3b5c' }
const PALETTE = ['#38d6f5', '#ff3b5c', '#f5c518', '#2fd98a', '#8b5cf6', '#ff8a3d', '#6f8fff']

export function ThreatTrendChart({ data = [] }) {
  const rows = useMemo(
    () => data.map((d) => ({ ...d, t: formatAxisTime(d.time) })),
    [data],
  )
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={rows} margin={{ top: 6, right: 10, bottom: 0, left: -22 }}>
        <defs>
          <linearGradient id="gBenign" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38d6f5" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#38d6f5" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="gThreat" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff3b5c" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#ff3b5c" stopOpacity={0.03} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} width={44} allowDecimals={false} />
        <CartesianGrid {...GRID} vertical={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Area type="monotone" dataKey="benign" stackId="1" stroke="#38d6f5" strokeWidth={1.5} fill="url(#gBenign)" name="Benign" />
        <Area type="monotone" dataKey="threat" stackId="1" stroke="#ff3b5c" strokeWidth={1.5} fill="url(#gThreat)" name="Threat" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function CategoryChart({ data = [] }) {
  const rows = data.filter((d) => d.value > 0)
  if (!rows.length) {
    return (
      <div className="grid h-full place-items-center text-center text-[11px] text-slate-500">
        No threat categories recorded yet.
      </div>
    )
  }
  return (
    <div className="flex h-full items-center gap-2">
      <ResponsiveContainer width="58%" height="100%">
        <PieChart>
          <Pie data={rows} dataKey="value" nameKey="name" innerRadius="56%" outerRadius="86%" paddingAngle={2} stroke="none">
            {rows.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip {...TOOLTIP_STYLE} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="flex-1 space-y-1.5 pr-2">
        {rows.map((d, i) => (
          <li key={d.name} className="flex items-center gap-2 text-[11px]">
            <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: PALETTE[i % PALETTE.length] }} />
            <span className="min-w-0 flex-1 truncate text-slate-400">{d.name}</span>
            <span className="mono text-slate-200">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function RiskHistoryChart({ data = [] }) {
  const rows = useMemo(() => data.map((d) => ({ t: formatAxisTime(d.time), score: d.score })), [data])
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 6, right: 10, bottom: 0, left: -22 }}>
        <XAxis dataKey="t" {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} width={44} domain={[0, 100]} />
        <CartesianGrid {...GRID} vertical={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Line type="monotone" dataKey="score" stroke="#2fd98a" strokeWidth={2} dot={false} name="Security score" />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function EventVolumeChart({ data = [] }) {
  const rows = useMemo(() => data.map((d) => ({ t: formatAxisTime(d.time), count: d.count })), [data])
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 6, right: 10, bottom: 0, left: -22 }} barCategoryGap="26%">
        <XAxis dataKey="t" {...AXIS} interval="preserveStartEnd" />
        <YAxis {...AXIS} width={44} allowDecimals={false} />
        <CartesianGrid {...GRID} vertical={false} />
        <Tooltip {...TOOLTIP_STYLE} />
        <Bar dataKey="count" fill="#12b6dd" radius={[3, 3, 0, 0]} name="Events" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function SeverityChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 12 }} barCategoryGap="28%">
        <XAxis type="number" {...AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="severity" {...AXIS} width={68} />
        <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <Bar dataKey="count" radius={[0, 3, 3, 0]} name="Threats">
          {data.map((d) => (
            <Cell key={d.severity} fill={SEV_COLORS[d.severity] || '#38d6f5'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
