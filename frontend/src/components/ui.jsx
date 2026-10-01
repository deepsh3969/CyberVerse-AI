import React from 'react'
import { severityBgClass, severityClass } from '../utils/format'

export function Panel({ title, subtitle, action, children, className = '', bodyClassName = '', icon = null }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-3 border-b border-white/[0.06] px-4 py-3">
          <div className="flex items-start gap-2">
            {icon && <span className="mt-0.5 text-cyber-400">{icon}</span>}
            <div>
              {title && <h3 className="text-sm font-semibold text-slate-100">{title}</h3>}
              {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
            </div>
          </div>
          {action}
        </header>
      )}
      <div className={`p-4 ${bodyClassName}`}>{children}</div>
    </section>
  )
}

export function SectionHeading({ eyebrow, title, description, actions }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="label-caps mb-1">{eyebrow}</p>}
        <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function SeverityBadge({ severity, className = '' }) {
  const sev = (severity || 'INFO').toUpperCase()
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wider ${severityBgClass(sev)} ${severityClass(sev)} ${className}`}
    >
      {sev}
    </span>
  )
}

export function StatusPill({ status, className = '' }) {
  const map = {
    OPEN: 'border-alert-500/40 bg-alert-500/10 text-alert-400',
    INVESTIGATING: 'border-warn-500/40 bg-warn-500/10 text-warn-400',
    CONTAINED: 'border-cyber-400/40 bg-cyber-400/10 text-cyber-300',
    RESOLVED: 'border-ok-400/40 bg-ok-400/10 text-ok-400',
  }
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] font-semibold tracking-wider ${
        map[status] || 'border-white/15 bg-white/5 text-slate-300'
      } ${className}`}
    >
      {status}
    </span>
  )
}

export function StatusDot({ status, size = 8, pulse = false }) {
  const colors = {
    healthy: '#2fd98a',
    warning: '#f5c518',
    compromised: '#ff3b5c',
    monitoring: '#6f8fff',
    contained: '#38d6f5',
  }
  const color = colors[(status || '').toLowerCase()] || '#94a3b8'
  return (
    <span
      className={`inline-block rounded-full ${pulse ? 'animate-pulseDot' : ''}`}
      style={{ width: size, height: size, backgroundColor: color, boxShadow: `0 0 10px ${color}80` }}
      aria-hidden="true"
    />
  )
}

export function StatTile({ label, value, sub, accent = 'cyber', icon = null, trend = null }) {
  const accents = {
    cyber: 'border-cyber-400/25 text-cyber-300',
    alert: 'border-alert-500/30 text-alert-400',
    warn: 'border-warn-500/30 text-warn-400',
    ok: 'border-ok-400/30 text-ok-400',
    slate: 'border-white/10 text-slate-200',
  }
  return (
    <div className={`card card-hover relative overflow-hidden p-4 ${accents[accent] || accents.slate}`}>
      <div className="flex items-center justify-between">
        <p className="label-caps">{label}</p>
        {icon && <span className="opacity-70">{icon}</span>}
      </div>
      <p className="mono mt-2 text-2xl font-semibold tracking-tight text-white sm:text-[26px]">{value}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        {sub && <p className="text-xs text-slate-400">{sub}</p>}
        {trend && <span className="text-[11px] text-slate-500">{trend}</span>}
      </div>
      <span className="absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-current to-transparent opacity-40" />
    </div>
  )
}

export function EmptyState({ icon = null, title, message, action = null }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-white/[0.02] px-6 py-10 text-center">
      {icon && <div className="mb-3 text-slate-500">{icon}</div>}
      <p className="text-sm font-medium text-slate-200">{title}</p>
      {message && <p className="mt-1 max-w-md text-xs leading-relaxed text-slate-500">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function Spinner({ size = 16, className = '' }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-current border-r-transparent ${className}`}
      style={{ width: size, height: size }}
      role="status"
      aria-label="loading"
    />
  )
}

export function ProgressBar({ value, max = 100, color = '#38d6f5', height = 6, label }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div>
      {label && (
        <div className="mb-1 flex items-center justify-between text-[11px] text-slate-400">
          <span>{label}</span>
          <span className="mono">{Math.round(pct)}%</span>
        </div>
      )}
      <div className="w-full overflow-hidden rounded-full bg-white/[0.07]" style={{ height }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color, boxShadow: `0 0 12px ${color}66` }}
        />
      </div>
    </div>
  )
}

export function ToolbarButton({ children, onClick, icon: Icon, variant = 'ghost', disabled, title, type = 'button' }) {
  const cls = variant === 'primary' ? 'btn-primary' : variant === 'danger' ? 'btn-danger' : 'btn-ghost'
  return (
    <button type={type} className={cls} onClick={onClick} disabled={disabled} title={title}>
      {Icon && <Icon size={15} />}
      {children}
    </button>
  )
}

export function DefinitionRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/[0.05] py-2 last:border-0">
      <span className="label-caps shrink-0">{label}</span>
      <span className="text-right text-sm text-slate-200">{value}</span>
    </div>
  )
}
