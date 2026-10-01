import React, { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  Boxes,
  BrainCircuit,
  FlaskConical,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Radio,
  Settings as SettingsIcon,
  ShieldAlert,
  Share2,
  X,
} from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import Toasts from '../components/Toasts'
import { DemoCompact } from '../components/DemoController'
import { formatTime } from '../utils/format'

const NAV = [
  { to: '/app', end: true, label: 'Overview', icon: LayoutDashboard },
  { to: '/app/network', label: '3D Network', icon: Boxes },
  { to: '/app/threats', label: 'Threats', icon: ShieldAlert },
  { to: '/app/attack-graph', label: 'Attack Graph', icon: Share2 },
  { to: '/app/ai-analyst', label: 'AI Analyst', icon: BrainCircuit },
  { to: '/app/simulator', label: 'Simulator', icon: FlaskConical },
  { to: '/app/incidents', label: 'Incidents', icon: Activity },
  { to: '/app/reports', label: 'Reports', icon: FileText },
  { to: '/app/settings', label: 'Settings', icon: SettingsIcon },
]

function NavItems({ onNavigate }) {
  const { incidents } = useApp()
  const openCount = incidents.filter((i) => i.status === 'OPEN' || i.status === 'INVESTIGATING').length
  return (
    <nav className="flex flex-col gap-0.5 px-2">
      {NAV.map(({ to, end, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
              isActive
                ? 'bg-cyber-400/[0.1] text-cyber-300'
                : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <span
                className={`absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full transition ${
                  isActive ? 'bg-cyber-400 opacity-100' : 'opacity-0'
                }`}
              />
              <Icon size={16} className="shrink-0" />
              <span className="flex-1">{label}</span>
              {label === 'Incidents' && openCount > 0 && (
                <span className="mono rounded bg-alert-500/20 px-1.5 py-0.5 text-[10px] text-alert-400">
                  {openCount}
                </span>
              )}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function ConnectionPill() {
  const { online, health, settings } = useApp()
  const state = online === null ? 'checking' : online ? 'online' : 'offline'
  const styles = {
    checking: 'border-white/15 text-slate-400',
    online: 'border-ok-400/40 text-ok-400',
    offline: 'border-alert-500/40 text-alert-400',
  }
  return (
    <div
      className={`hidden items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] sm:flex ${styles[state]}`}
      title={health ? `ML: ${health.ml_backend} · DB: ${health.database}` : 'Backend not reachable'}
    >
      <Radio size={12} className={state === 'online' ? 'animate-pulseDot' : ''} />
      <span className="mono uppercase tracking-wider">
        {state === 'online' ? 'Live' : state === 'checking' ? 'Checking' : 'Offline mode'}
      </span>
      <span className="hidden text-slate-500 lg:inline">· {settings?.ai_provider}</span>
    </div>
  )
}

function OperatorBadge() {
  const { authEnabled, user, logout } = useAuth()
  const navigate = useNavigate()

  if (!authEnabled || !user) return null
  return (
    <div className="flex items-center gap-2.5">
      <div className="hidden text-right leading-tight sm:block">
        <p className="max-w-[160px] truncate text-[12px] text-slate-300">{user.full_name || user.email}</p>
        <p className="mono text-[9.5px] uppercase tracking-[0.16em] text-cyber-600">{user.role}</p>
      </div>
      <button
        className="btn-ghost px-2.5 py-1.5 text-xs"
        onClick={async () => {
          await logout()
          navigate('/login')
        }}
        title="Sign out"
        aria-label="Sign out"
      >
        <LogOut size={14} />
        <span className="hidden sm:inline">Sign out</span>
      </button>
    </div>
  )
}

export default function CommandCenterLayout() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  const { offline, dashboard, updatedAt } = useApp()

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  return (
    <div className="flex min-h-screen">
      {/* sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[236px] flex-col border-r border-white/[0.07] bg-ink-900/80 backdrop-blur no-print lg:flex">
        <div className="flex h-14 items-center gap-2.5 border-b border-white/[0.07] px-4">
          <span className="grid h-7 w-7 place-items-center rounded-md border border-cyber-400/40 bg-cyber-400/10">
            <ShieldAlert size={15} className="text-cyber-400" />
          </span>
          <div className="leading-tight">
            <p className="text-[13px] font-semibold tracking-wide text-white">CYBERVERSE AI</p>
            <p className="mono text-[9.5px] uppercase tracking-[0.18em] text-cyber-600">Command Center</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-3">
          <p className="label-caps px-4 pb-2">Operations</p>
          <NavItems />
        </div>

        <div className="border-t border-white/[0.07] p-3">
          <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <div className="flex items-center justify-between">
              <p className="label-caps">Security score</p>
              <span className="mono text-sm font-semibold text-white">{dashboard?.security_score ?? '—'}</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.07]">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${dashboard?.security_score ?? 0}%`,
                  backgroundColor: dashboard?.threat_level?.color || '#38d6f5',
                }}
              />
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              {dashboard?.active_incidents ?? 0} active incident
              {(dashboard?.active_incidents ?? 0) === 1 ? '' : 's'} · updated{' '}
              <span className="mono">{updatedAt ? formatTime(updatedAt / 1000) : '—'}</span>
            </p>
          </div>
        </div>
      </aside>

      {/* mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden no-print">
          <div className="absolute inset-0 bg-black/70" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-[260px] border-r border-white/10 bg-ink-900 p-3">
            <div className="mb-3 flex items-center justify-between px-2">
              <p className="text-sm font-semibold text-white">CYBERVERSE AI</p>
              <button onClick={() => setOpen(false)} aria-label="Close menu" className="text-slate-400">
                <X size={18} />
              </button>
            </div>
            <NavItems onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}

      {/* main */}
      <div className="flex min-w-0 flex-1 flex-col lg:ml-[236px]">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-white/[0.07] bg-ink-950/85 px-3 backdrop-blur no-print sm:px-5">
          <button
            className="rounded-md border border-white/10 p-1.5 text-slate-300 lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={17} />
          </button>

          <div className="min-w-0 flex-1">
            <p className="truncate text-[13px] font-medium text-slate-200">
              {NAV.find((n) => (n.end ? pathname === n.to : pathname.startsWith(n.to)))?.label || 'Overview'}
            </p>
            <p className="mono hidden text-[10px] uppercase tracking-[0.16em] text-slate-600 sm:block">
              SEE THE ATTACK · UNDERSTAND THE THREAT · STOP IT
            </p>
          </div>

          <ConnectionPill />
          <OperatorBadge />
          <DemoCompact />
        </header>

        {offline && (
          <div className="border-b border-warn-500/25 bg-warn-500/[0.07] px-4 py-2 text-[12px] text-warn-400 no-print">
            Backend unreachable — showing bundled preview data. Start the API (<span className="mono">npm run
            dev:api</span> in <span className="mono">backend/</span>) to enable live detection, simulation and AI
            analysis.
          </div>
        )}

        <main className="min-w-0 flex-1 px-3 py-4 sm:px-5 sm:py-5">
          <Outlet />
        </main>

        <footer className="border-t border-white/[0.05] px-5 py-3 text-[11px] text-slate-600 no-print">
          CyberVerse AI · defensive simulation platform · all events and attacks are synthetic and contained in
          this sandbox
        </footer>
      </div>

      <Toasts />
    </div>
  )
}
