import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Activity,
  ArrowRight,
  Boxes,
  BrainCircuit,
  FileText,
  GitBranch,
  PlayCircle,
  Radar,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react'
import HeroScene from '../three/HeroScene'
import { useApp } from '../context/AppContext'

const STORY = [
  { label: 'NORMAL', note: 'Baseline telemetry', color: '#2fd98a' },
  { label: 'ANOMALY', note: 'Deviation detected', color: '#f5c518' },
  { label: 'THREAT', note: 'Classified + scored', color: '#ff8a3d' },
  { label: 'INVESTIGATION', note: 'AI explains', color: '#38d6f5' },
  { label: 'ATTACK PATH', note: 'Graph reconstructed', color: '#ff3b5c' },
  { label: 'RESPONSE', note: 'Actions recommended', color: '#8b5cf6' },
  { label: 'CONTAINMENT', note: 'Threat isolated', color: '#38d6f5' },
  { label: 'RECOVERY', note: 'Secure state', color: '#2fd98a' },
]

const CAPABILITIES = [
  {
    icon: Boxes,
    title: '3D Cyber Network',
    body: 'Orbit a live map of the infrastructure. Nodes change state the moment a threat is detected and attack paths light up in real time.',
  },
  {
    icon: Radar,
    title: 'Safe Attack Simulator',
    body: 'Eight synthetic scenarios — brute force, exfiltration, DDoS, insider threat — generating realistic event sequences inside a sandbox.',
  },
  {
    icon: BrainCircuit,
    title: 'ML Detection Engine',
    body: 'Isolation Forest anomaly scoring combined with an explainable rule engine returns threat type, confidence, risk and evidence.',
  },
  {
    icon: GitBranch,
    title: 'Attack Graph',
    body: 'Reconstructed lateral path from external attacker to crown-jewel data, with timestamps, severity and per-node risk.',
  },
  {
    icon: Activity,
    title: 'Incident Management',
    body: 'Cases carry evidence, timeline, status workflow, AI analysis and a contextual defensive playbook.',
  },
  {
    icon: ShieldCheck,
    title: 'Containment Simulation',
    body: 'One click isolates the endpoint, terminates the session and blocks the threat path — fully simulated, fully traceable.',
  },
]

export default function Landing() {
  const navigate = useNavigate()
  const { actions, offline, demo } = useApp()
  const [busy, setBusy] = useState(false)

  const runDemo = async () => {
    if (busy) return
    setBusy(true)
    try {
      if (!offline) {
        if (demo?.state === 'complete' || demo?.state === 'aborted' || demo?.state === 'failed') {
          await actions.resetDemo()
        }
        await actions.startDemo()
      }
      navigate('/app')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-ink-950/80 backdrop-blur no-print">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-md border border-cyber-400/40 bg-cyber-400/10">
              <ShieldAlert size={15} className="text-cyber-400" />
            </span>
            <div className="leading-tight">
              <p className="text-[13px] font-semibold tracking-wide text-white">CYBERVERSE AI</p>
              <p className="mono text-[9px] uppercase tracking-[0.18em] text-cyber-600">Defensive SOC Platform</p>
            </div>
          </div>
          <nav className="hidden items-center gap-6 text-[13px] text-slate-400 md:flex">
            <a href="#capabilities" className="transition hover:text-cyber-300">Capabilities</a>
            <a href="#pipeline" className="transition hover:text-cyber-300">How it works</a>
            <a href="#stack" className="transition hover:text-cyber-300">Stack</a>
            <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => navigate('/app')}>
              Open Console <ArrowRight size={13} />
            </button>
          </nav>
          <button className="btn-ghost px-3 py-1.5 text-xs md:hidden" onClick={() => navigate('/app')}>
            Console
          </button>
        </div>
      </header>

      {/* HERO */}
      <section className="relative overflow-hidden border-b border-white/[0.06] grid-bg">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-4 py-12 sm:px-6 lg:grid-cols-2 lg:py-16">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="no-print"
          >
            <p className="label-caps mb-4 flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-alert-500 animate-pulseDot" />
              AI-Powered Cybersecurity Command Center
            </p>
            <h1 className="text-4xl font-bold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-6xl">
              CYBERVERSE <span className="text-cyber-400">AI</span>
            </h1>
            <p className="mono mt-4 text-[13px] uppercase tracking-[0.24em] text-slate-400 sm:text-sm">
              Detect. Investigate. Visualize. Respond.
            </p>
            <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-slate-400">
              A 3D security operations center for your simulated infrastructure. Watch synthetic attacks unfold,
              let the detection engine classify them, read the AI investigation, follow the attack graph, and
              contain the threat — all in one console.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button className="btn-primary px-5 py-2.5 text-sm" onClick={() => navigate('/app')}>
                <ShieldCheck size={16} /> Enter Command Center
              </button>
              <button className="btn-ghost px-5 py-2.5 text-sm" onClick={runDemo} disabled={busy || offline}
                title={offline ? 'Backend offline — start the API to run the demo' : 'Run the scripted scenario'}>
                <PlayCircle size={16} /> Run Demo
              </button>
            </div>
            <dl className="mt-9 grid max-w-lg grid-cols-3 gap-4 border-t border-white/[0.07] pt-5">
              {[
                ['8', 'Attack scenarios'],
                ['10', 'Monitored assets'],
                ['100%', 'Synthetic telemetry'],
              ].map(([v, l]) => (
                <div key={l}>
                  <dt className="mono text-xl font-semibold text-white">{v}</dt>
                  <dd className="mt-0.5 text-[11px] text-slate-500">{l}</dd>
                </div>
              ))}
            </dl>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="relative h-[340px] overflow-hidden rounded-2xl border border-white/[0.08] bg-ink-900/60 sm:h-[420px]"
          >
            <HeroScene />
            <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-md border border-white/10 bg-ink-950/70 px-2.5 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-ok-400 animate-pulseDot" />
              <span className="mono text-[10px] uppercase tracking-wider text-slate-400">Live topology · drag to orbit</span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* STORY RIBBON */}
      <section id="pipeline" className="border-b border-white/[0.06] bg-ink-900/40">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
          <div className="mb-5 flex items-end justify-between">
            <div>
              <p className="label-caps">The story in 30 seconds</p>
              <h2 className="mt-1 text-lg font-semibold text-white">From normal traffic to containment</h2>
            </div>
            <FileText size={16} className="hidden text-slate-600 sm:block" />
          </div>
          <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
            {STORY.map((s, i) => (
              <li
                key={s.label}
                className="relative rounded-lg border border-white/[0.07] bg-white/[0.02] p-3 transition hover:bg-white/[0.045]"
                style={{ borderTopColor: s.color, borderTopWidth: 2 }}
              >
                <span className="mono text-[10px] text-slate-600">0{i + 1}</span>
                <p className="mt-1 text-[11.5px] font-semibold tracking-wide" style={{ color: s.color }}>
                  {s.label}
                </p>
                <p className="mt-0.5 text-[10.5px] leading-snug text-slate-500">{s.note}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* CAPABILITIES */}
      <section id="capabilities" className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <p className="label-caps">Capabilities</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">Everything a SOC analyst needs, in one pane</h2>
        <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map(({ icon: Icon, title, body }) => (
            <article key={title} className="card card-hover p-5">
              <span className="grid h-9 w-9 place-items-center rounded-lg border border-cyber-400/25 bg-cyber-400/[0.08] text-cyber-400">
                <Icon size={17} />
              </span>
              <h3 className="mt-4 text-[15px] font-semibold text-white">{title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-400">{body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* STACK */}
      <section id="stack" className="border-t border-white/[0.06] bg-ink-900/40">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
          <div className="grid gap-6 lg:grid-cols-3">
            <div>
              <p className="label-caps">Built with</p>
              <h2 className="mt-1 text-lg font-semibold text-white">Modern, boring, reliable stack</h2>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-400">
                React + Vite + Tailwind on the front, FastAPI + scikit-learn behind it. The detection engine
                runs locally, so the product works with no external AI key and no GPU.
              </p>
            </div>
            <div className="lg:col-span-2">
              <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {[
                  'React 18', 'Vite', 'Tailwind CSS', 'Three.js / R3F', 'Recharts', 'Framer Motion',
                  'FastAPI', 'Pydantic', 'scikit-learn', 'Isolation Forest', 'NumPy / pandas', 'MongoDB (optional)',
                ].map((t) => (
                  <li
                    key={t}
                    className="mono rounded-lg border border-white/[0.07] bg-white/[0.02] px-3 py-2 text-[11.5px] text-slate-400"
                  >
                    {t}
                  </li>
                ))}
              </ul>
              <p className="mt-4 flex items-start gap-2 text-[11.5px] leading-relaxed text-slate-500">
                <ShieldAlert size={14} className="mt-0.5 shrink-0 text-warn-400" />
                Defensive simulation only. No real systems are scanned, exploited or contacted — every event is
                generated inside this application.
              </p>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/[0.06] px-4 py-6 no-print">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 sm:flex-row">
          <p className="text-[12px] text-slate-500">
            CyberVerse AI · SEE THE ATTACK. UNDERSTAND THE THREAT. STOP IT.
          </p>
          <button className="btn-primary text-xs" onClick={() => navigate('/app')}>
            Enter Command Center <ArrowRight size={14} />
          </button>
        </div>
      </footer>
    </div>
  )
}
