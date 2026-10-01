import React, { useState } from 'react'
import { CheckCircle2, Database, KeyRound, MonitorCog, RotateCcw, ShieldAlert, Volume2 } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { useAuth } from '../context/AuthContext'
import { apiBase } from '../services/api'
import { Panel, SectionHeading, Spinner } from '../components/ui'
import { playTone } from '../utils/prefs'

const REFRESH_OPTIONS = [
  { value: 2000, label: '2 seconds (fast)' },
  { value: 4000, label: '4 seconds (default)' },
  { value: 8000, label: '8 seconds (calm)' },
  { value: 15000, label: '15 seconds (low power)' },
]

const THEMES = [
  { value: 'command', label: 'Command (default)' },
  { value: 'midnight', label: 'Midnight (deep black)' },
  { value: 'tactical', label: 'Tactical (lighter panels)' },
]

function Row({ label, hint, children }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.05] py-3 last:border-0">
      <div className="min-w-0">
        <p className="text-[13.5px] font-medium text-slate-200">{label}</p>
        {hint && <p className="mt-0.5 max-w-lg text-[12px] text-slate-500">{hint}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

export default function Settings() {
  const { settings, health, offline, actions, prefs, setPrefs, pushToast } = useApp()
  const { canWrite, isAdmin, authEnabled, user } = useAuth()
  const [testing, setTesting] = useState(false)

  const testConnection = async () => {
    setTesting(true)
    const ok = await actions.checkHealth()
    setTesting(false)
    pushToast({
      type: ok ? 'success' : 'error',
      title: ok ? 'Backend reachable' : 'Backend unreachable',
      message: ok ? `Version ${health?.version || ''} · ML ${health?.ml_backend || ''}` : 'Check VITE_API_URL and that the API is running.',
    })
  }

  return (
    <div className="space-y-4">
      <SectionHeading
        eyebrow="Configuration"
        title="Settings"
        description="Runtime preferences are stored locally in your browser. Secrets are never sent to the frontend — they live in backend environment variables."
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <Panel title="Connection" subtitle="Where the console talks to the API" icon={<Database size={14} />}>
          <Row label="API endpoint" hint="Set VITE_API_URL at build time; empty means same-origin /api (dev proxy).">
            <span className="mono rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-[11.5px] text-slate-300">
              {apiBase || '/api (proxied)'}
            </span>
          </Row>
          <Row label="Status" hint={offline ? 'The backend is not responding.' : 'Live data is streaming.'}>
            <span className={`flex items-center gap-2 text-[12.5px] ${offline ? 'text-alert-400' : 'text-ok-400'}`}>
              <span className={`h-2 w-2 rounded-full ${offline ? 'bg-alert-500' : 'bg-ok-400 animate-pulseDot'}`} />
              {offline ? 'Offline' : 'Connected'}
            </span>
          </Row>
          <Row label="Test connection" hint="Runs a health check against the API.">
            <button className="btn-ghost text-xs" onClick={testConnection} disabled={testing}>
              {testing ? <Spinner size={13} /> : <CheckCircle2 size={13} />} Test now
            </button>
          </Row>
          <Row label="API version" hint={`Uptime ${health ? Math.round(health.uptime_seconds) : 0}s`}>
            <span className="mono text-[12px] text-slate-300">{health?.version || '—'}</span>
          </Row>
          <Row label="Database mode" hint="mongodb when MONGODB_URI is configured, otherwise in-memory demo mode.">
            <span className="mono text-[12px] text-slate-300">{settings?.database || health?.database || '—'}</span>
          </Row>
          <Row label="Rate limit" hint="Requests allowed per minute per client.">
            <span className="mono text-[12px] text-slate-300">{settings?.rate_limit_per_minute ?? '—'}/min</span>
          </Row>
        </Panel>

        <Panel title="AI provider" subtitle="How incident explanations are produced" icon={<KeyRound size={14} />}>
          <Row label="Active provider" hint="Falls back automatically when no external key is configured.">
            <span className="mono text-[12px] text-cyber-300">{settings?.ai_provider || 'local-analysis-engine'}</span>
          </Row>
          <Row label="Model" hint="Used only when an external provider is configured.">
            <span className="mono text-[12px] text-slate-300">{settings?.ai_model || 'local rules + isolation forest'}</span>
          </Row>
          <Row label="Detection backend" hint="Unsupervised anomaly model trained locally at startup.">
            <span className="mono text-[12px] text-slate-300">{settings?.ml_backend || health?.ml_backend || '—'}</span>
          </Row>
          <div className="mt-3 rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <p className="label-caps mb-1.5">Backend environment variables (never exposed to the browser)</p>
            <ul className="mono space-y-1 text-[11.5px] text-slate-500">
              <li>MONGODB_URI — optional persistence</li>
              <li>AI_API_KEY — optional external LLM</li>
              <li>AI_API_BASE / AI_MODEL / AI_PROVIDER</li>
              <li>CORS_ORIGINS — allowed frontend origins</li>
              <li>RATE_LIMIT_PER_MINUTE</li>
            </ul>
          </div>
        </Panel>

        <Panel title="Interface" subtitle="Stored in this browser only" icon={<MonitorCog size={14} />}>
          <Row label="Animation intensity" hint="Controls packet density in the 3D network.">
            <div className="flex items-center gap-2">
              <input
                type="range"
                min="0"
                max="2"
                step="0.5"
                value={prefs.animationIntensity}
                onChange={(e) => setPrefs({ animationIntensity: Number(e.target.value) })}
                className="w-32 accent-cyber-400"
                aria-label="Animation intensity"
              />
              <span className="mono w-8 text-[12px] text-slate-300">{prefs.animationIntensity}x</span>
            </div>
          </Row>
          <Row label="Sound effects" hint="A short tone when a new threat is detected.">
            <label className="flex cursor-pointer items-center gap-2 text-[12.5px] text-slate-300">
              <input
                type="checkbox"
                checked={prefs.sound}
                onChange={(e) => setPrefs({ sound: e.target.checked })}
                className="accent-cyber-400"
              />
              <Volume2 size={14} />
              {prefs.sound ? 'On' : 'Off'}
            </label>
          </Row>
          <Row label="Test tone" hint="Preview the alert sound.">
            <button className="btn-ghost text-xs" onClick={() => playTone('warn')}>
              <Volume2 size={13} /> Play
            </button>
          </Row>
          <Row label="Theme" hint="Visual variant of the command center.">
            <select
              className="input w-auto py-1.5 text-xs"
              value={prefs.theme}
              onChange={(e) => setPrefs({ theme: e.target.value })}
              aria-label="Theme"
            >
              {THEMES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </Row>
          <Row label="Refresh interval" hint="How often the console polls the API.">
            <select
              className="input w-auto py-1.5 text-xs"
              value={prefs.refreshInterval}
              onChange={(e) => setPrefs({ refreshInterval: Number(e.target.value) })}
              aria-label="Refresh interval"
            >
              {REFRESH_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </Row>
          <Row label="Demo shortcuts" hint="Show the hackathon demo controls in the header and overview.">
            <input
              type="checkbox"
              checked={prefs.demoMode}
              onChange={(e) => setPrefs({ demoMode: e.target.checked })}
              className="h-4 w-4 accent-cyber-400"
              aria-label="Enable demo controls"
            />
          </Row>
        </Panel>

        <Panel title="Sandbox controls" subtitle="Everything here changes simulated state only" icon={<ShieldAlert size={14} />}>
          <Row label="Reset demo sequence" hint="Restores the scripted walkthrough to its starting state.">
            <button
              className="btn-ghost text-xs"
              onClick={actions.resetDemo}
              disabled={offline || !canWrite}
              title={canWrite ? undefined : 'Analyst role required'}
            >
              <RotateCcw size={13} /> Reset demo
            </button>
          </Row>
          <Row
            label="Reset sandbox"
            hint="Clears events, threats, incidents and node states, then reseeds baseline data."
          >
            <button
              className="btn-danger text-xs"
              onClick={actions.resetSandbox}
              disabled={offline || !isAdmin}
              title={isAdmin ? undefined : 'Admin role required'}
            >
              <RotateCcw size={13} /> Reset sandbox
            </button>
          </Row>
          <Row label="Assets under management" hint="Nodes in the simulated topology.">
            <span className="mono text-[12px] text-slate-300">{settings?.assets ?? '—'}</span>
          </Row>
          <Row
            label="Access control"
            hint={
              authEnabled
                ? 'Authentication is enforced: writes require analyst or admin, resets and user management require admin.'
                : 'Demo deployment: the API accepts unauthenticated requests (no database configured).'
            }
          >
            <span className="mono text-[12px] text-slate-300">
              {authEnabled && user ? `${user.email} · ${user.role}` : authEnabled ? 'not signed in' : 'open demo'}
            </span>
          </Row>
          <div className="mt-3 rounded-lg border border-warn-500/25 bg-warn-500/[0.06] p-3 text-[12px] leading-relaxed text-warn-400">
            CyberVerse AI performs defensive simulation only. It does not scan, probe, exploit or otherwise
            interact with any real system, credential or network outside this application.
          </div>
        </Panel>
      </div>
    </div>
  )
}
