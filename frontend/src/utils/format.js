export const formatNumber = (n) => {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '0'
  return Number(n).toLocaleString('en-US')
}

export const formatTime = (ts, { seconds = true } = {}) => {
  if (!ts) return '—'
  const d = new Date(Number(ts) * (ts > 1e12 ? 1 : 1000))
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    ...(seconds ? { second: '2-digit' } : {}),
  })
}

export const formatDateTime = (ts) => {
  if (!ts) return '—'
  const d = new Date(Number(ts) * (ts > 1e12 ? 1 : 1000))
  if (Number.isNaN(d.getTime())) return '—'
  return `${d.toLocaleDateString('en-GB')} ${d.toLocaleTimeString('en-GB')}`
}

export const relativeTime = (ts) => {
  if (!ts) return '—'
  const ms = Date.now() - Number(ts) * (ts > 1e12 ? 1 : 1000)
  const s = Math.round(ms / 1000)
  if (Math.abs(s) < 60) return `${s}s ago`
  const m = Math.round(s / 60)
  if (Math.abs(m) < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  if (Math.abs(h) < 48) return `${h}h ago`
  return `${Math.round(h / 24)}d ago`
}

export const severityClass = (sev) => `severity-${(sev || 'INFO').toUpperCase()}`
export const severityBgClass = (sev) => `severity-bg-${(sev || 'INFO').toUpperCase()}`

export const statusColor = (status) => {
  switch ((status || '').toLowerCase()) {
    case 'compromised':
      return '#ff3b5c'
    case 'warning':
      return '#f5c518'
    case 'contained':
      return '#38d6f5'
    case 'monitoring':
      return '#6f8fff'
    default:
      return '#2fd98a'
  }
}

export const incidentStatusColor = (status) => {
  switch ((status || '').toUpperCase()) {
    case 'OPEN':
      return 'text-alert-400'
    case 'INVESTIGATING':
      return 'text-warn-400'
    case 'CONTAINED':
      return 'text-cyber-400'
    case 'RESOLVED':
      return 'text-ok-400'
    default:
      return 'text-slate-300'
  }
}

export const riskBand = (score) => {
  if (score >= 85) return { label: 'CRITICAL', color: '#ff3b5c' }
  if (score >= 70) return { label: 'HIGH', color: '#ff8a3d' }
  if (score >= 50) return { label: 'MEDIUM', color: '#f5c518' }
  return { label: 'LOW', color: '#2fd98a' }
}

export const clamp = (v, min, max) => Math.max(min, Math.min(max, v))
