import React from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowUpRight,
  Database,
  Gauge,
  Layers,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import StoryRibbon from '../components/StoryRibbon'
import DemoController from '../components/DemoController'
import EventConsole from '../components/EventConsole'
import { Panel, SectionHeading, SeverityBadge, Spinner, StatTile, StatusDot, StatusPill, EmptyState } from '../components/ui'
import { ChartFrame } from '../charts/common'
import {
  CategoryChart,
  EventVolumeChart,
  RiskHistoryChart,
  SeverityChart,
  ThreatTrendChart,
} from '../charts/DashboardCharts'
import { formatNumber, relativeTime, riskBand, severityClass } from '../utils/format'

export default function Overview() {
  const { dashboard, threats, events, loading, actions, offline, settings } = useApp()
  const band = riskBand(dashboard.security_score)

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Security operations"
        title="Overview"
        description="Live posture of the simulated infrastructure: detection throughput, open cases and risk trajectory."
        actions={
          <>
            <button className="btn-ghost text-xs" onClick={actions.refresh} disabled={loading}>
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
            </button>
            <Link to="/app/simulator" className="btn-primary text-xs">
              <ShieldAlert size={14} /> Run simulation
            </Link>
          </>
        }
      />

      <StoryRibbon />

      {/* KPI tiles */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        <StatTile
          label="AI Security Score"
          value={`${dashboard.security_score} / 100`}
          sub={dashboard.threat_level?.level === 'LOW' ? 'Posture healthy' : `Threat level ${dashboard.threat_level?.level}`}
          accent={dashboard.security_score >= 85 ? 'ok' : dashboard.security_score >= 65 ? 'warn' : 'alert'}
          icon={<Gauge size={15} />}
        />
        <StatTile
          label="Threat Level"
          value={dashboard.threat_level?.level || '—'}
          sub={`Index ${dashboard.threat_level?.score ?? 0}`}
          accent={dashboard.threat_level?.level === 'LOW' ? 'ok' : 'alert'}
          icon={<ShieldCheck size={15} />}
        />
        <StatTile
          label="Active Incidents"
          value={String(dashboard.active_incidents ?? 0).padStart(2, '0')}
          sub="Open or investigating"
          accent={dashboard.active_incidents ? 'alert' : 'ok'}
          icon={<Activity size={15} />}
        />
        <StatTile
          label="Events Analyzed"
          value={formatNumber(dashboard.events_analyzed)}
          sub={`ML backend: ${settings?.ml_backend || 'isolation-forest'}`}
          accent="cyber"
          icon={<Layers size={15} />}
        />
        <StatTile
          label="Threats Blocked"
          value={formatNumber(dashboard.threats_blocked)}
          sub="Through containment"
          accent="cyber"
          icon={<ShieldCheck size={15} />}
        />
        <StatTile
          label="Protected Assets"
          value={String(dashboard.protected_assets ?? 0)}
          sub="Nodes under watch"
          accent="slate"
          icon={<Database size={15} />}
        />
      </div>

      {/* chart row 1 */}
      <div className="grid gap-3 lg:grid-cols-3">
        <ChartFrame title="Threats over time" subtitle="Benign vs threat-flagged events · last hour" height={200}>
          <ThreatTrendChart data={dashboard.events_over_time} />
        </ChartFrame>
        <ChartFrame title="Threat categories" subtitle="Distribution across detected types" height={200}>
          <CategoryChart data={dashboard.threat_categories} />
        </ChartFrame>
        <ChartFrame title="Risk score history" subtitle="Rolling security score · lower is worse" height={200}>
          <RiskHistoryChart data={dashboard.risk_history} />
        </ChartFrame>
      </div>

      {/* chart row 2 */}
      <div className="grid gap-3 lg:grid-cols-3">
        <ChartFrame title="Event volume" subtitle="Events per minute · last 15 minutes" height={190}>
          <EventVolumeChart data={dashboard.event_volume} />
        </ChartFrame>
        <ChartFrame title="Attack severity distribution" subtitle="Detected threats by severity class" height={190}>
          <SeverityChart data={dashboard.severity_distribution} />
        </ChartFrame>
        <Panel title="Top assets at risk" subtitle="Ranked by current node risk score">
          <ul className="space-y-2.5">
            {(dashboard.top_assets || []).slice(0, 5).map((a) => (
              <li key={a.asset} className="flex items-center gap-3">
                <StatusDot status={a.status} />
                <span className="min-w-0 flex-1 truncate text-[13px] text-slate-300">{a.asset}</span>
                <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/[0.07]">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${a.risk}%`,
                      backgroundColor: riskBand(a.risk).color,
                    }}
                  />
                </div>
                <span className="mono w-7 text-right text-[11px] text-slate-400">{a.risk}</span>
              </li>
            ))}
            {!dashboard.top_assets?.length && <EmptyState title="No asset risk data" />}
          </ul>
        </Panel>
      </div>

      {/* threats + demo */}
      <div className="grid gap-3 lg:grid-cols-3">
        <Panel
          className="lg:col-span-2"
          title="Recent detections"
          subtitle="Highest-confidence findings from the detection engine"
          action={
            <Link to="/app/threats" className="flex items-center gap-1 text-[11.5px] text-cyber-400 hover:text-cyber-300">
              View all <ArrowUpRight size={13} />
            </Link>
          }
        >
          <div className="space-y-2">
            {threats.length === 0 && <EmptyState title="No threats recorded" message="Run a simulation to generate detections." />}
            {threats.slice(0, 5).map((t) => (
              <div
                key={t.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 transition hover:border-cyber-400/25"
              >
                <SeverityBadge severity={t.severity} />
                <span className="text-[13px] font-medium text-slate-100">{t.threat_type}</span>
                <span className="mono text-[11px] text-slate-500">{t.affected_asset}</span>
                <span className="mono text-[11px] text-slate-500">src {t.source}</span>
                <span className="ml-auto flex items-center gap-3">
                  <span className="mono text-[11px]" style={{ color: riskBand(t.risk_score).color }}>
                    risk {t.risk_score}
                  </span>
                  <span className="mono text-[11px] text-slate-500">conf {(t.confidence * 100).toFixed(0)}%</span>
                  <span className="mono hidden text-[11px] text-slate-600 sm:inline">{relativeTime(t.timestamp)}</span>
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <DemoController />
      </div>

      <EventConsole events={events} height={280} />
    </div>
  )
}
