import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowRight, Filter, RefreshCw } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { EmptyState, SectionHeading, SeverityBadge, StatusPill } from '../components/ui'
import { formatDateTime, relativeTime, riskBand } from '../utils/format'

const STATUSES = ['ALL', 'OPEN', 'INVESTIGATING', 'CONTAINED', 'RESOLVED']

export default function Incidents() {
  const { incidents, actions, offline, loading } = useApp()
  const { canWrite } = useAuth()
  const [status, setStatus] = useState('ALL')

  const filtered = useMemo(
    () => (status === 'ALL' ? incidents : incidents.filter((i) => i.status === status)),
    [incidents, status],
  )

  const counts = useMemo(() => {
    const c = { ALL: incidents.length }
    STATUSES.slice(1).forEach((s) => {
      c[s] = incidents.filter((i) => i.status === s).length
    })
    return c
  }, [incidents])

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Case management"
        title="Incidents"
        description="Every detected threat becomes a case with evidence, timeline, AI analysis, recommendations and a containment record."
        actions={
          <button className="btn-ghost text-xs" onClick={actions.refresh} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-1.5">
        <Filter size={13} className="mr-1 text-slate-500" />
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`rounded-md border px-2.5 py-1 text-[11px] font-medium transition ${
              status === s
                ? 'border-cyber-400/40 bg-cyber-400/10 text-cyber-300'
                : 'border-white/10 text-slate-400 hover:text-slate-200'
            }`}
          >
            {s} <span className="mono ml-1 text-slate-500">{counts[s] ?? 0}</span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<Activity size={24} />}
          title={status === 'ALL' ? 'No incidents recorded' : `No ${status.toLowerCase()} incidents`}
          message="Run a simulation or start the hackathon demo to open a case."
          action={
            <Link to="/app/simulator" className="btn-primary text-xs">
              Open simulator
            </Link>
          }
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left">
              <thead>
                <tr className="border-b border-white/[0.07] text-[10.5px] uppercase tracking-[0.14em] text-slate-500">
                  <th className="px-4 py-2.5 font-semibold">Incident</th>
                  <th className="px-4 py-2.5 font-semibold">Threat</th>
                  <th className="px-4 py-2.5 font-semibold">Severity</th>
                  <th className="px-4 py-2.5 font-semibold">Risk</th>
                  <th className="px-4 py-2.5 font-semibold">Affected assets</th>
                  <th className="px-4 py-2.5 font-semibold">First seen</th>
                  <th className="px-4 py-2.5 font-semibold">Status</th>
                  <th className="px-4 py-2.5 font-semibold" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((i) => (
                  <tr key={i.id} className="border-b border-white/[0.04] transition last:border-0 hover:bg-white/[0.03]">
                    <td className="px-4 py-3">
                      <Link to={`/app/incidents/${i.id}`} className="mono text-[12.5px] text-cyber-400 hover:text-cyber-300">
                        {i.id}
                      </Link>
                      <p className="text-[11px] text-slate-600">{i.source}</p>
                    </td>
                    <td className="px-4 py-3 text-[13px] text-slate-200">{i.threat_type}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={i.severity} /></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="mono text-[12.5px]" style={{ color: riskBand(i.risk_score).color }}>
                          {i.risk_score}
                        </span>
                        <div className="h-1.5 w-14 overflow-hidden rounded-full bg-white/[0.07]">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${i.risk_score}%`, backgroundColor: riskBand(i.risk_score).color }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="max-w-[220px] truncate px-4 py-3 text-[12.5px] text-slate-400">
                      {i.affected_assets?.join(', ')}
                    </td>
                    <td className="px-4 py-3">
                      <p className="mono text-[12px] text-slate-400">{formatDateTime(i.first_seen)}</p>
                      <p className="text-[11px] text-slate-600">{relativeTime(i.last_seen)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatusPill status={i.status} />
                        <select
                          className="rounded border border-white/10 bg-ink-900 px-1.5 py-0.5 text-[11px] text-slate-400 focus:border-cyber-400/50 focus:outline-none disabled:opacity-40"
                          value={i.status}
                          disabled={offline || !canWrite}
                          title={canWrite ? undefined : 'Analyst role required'}
                          onChange={(e) => actions.setIncidentStatus(i.id, e.target.value)}
                          aria-label={`Change status for ${i.id}`}
                        >
                          {STATUSES.slice(1).map((s) => (
                            <option key={s} value={s}>{s}</option>
                          ))}
                        </select>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/app/incidents/${i.id}`}
                        className="inline-flex items-center gap-1 text-[11.5px] text-slate-400 hover:text-cyber-300"
                      >
                        Open <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
