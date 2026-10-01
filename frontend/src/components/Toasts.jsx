import React from 'react'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useApp } from '../context/AppContext'

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const COLORS = {
  success: 'border-ok-400/40 text-ok-400',
  error: 'border-alert-500/40 text-alert-400',
  warning: 'border-warn-500/40 text-warn-400',
  info: 'border-cyber-400/40 text-cyber-300',
}

export default function Toasts() {
  const { toasts, dismissToast } = useApp()
  if (!toasts.length) return null
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[min(92vw,380px)] flex-col gap-2 no-print"
      role="region"
      aria-live="polite"
    >
      {toasts.map((t) => {
        const Icon = ICONS[t.type] || Info
        const color = COLORS[t.type] || COLORS.info
        return (
          <div
            key={t.id}
            className={`pointer-events-auto animate-slideUp rounded-lg border bg-ink-850/95 p-3 shadow-card backdrop-blur ${color}`}
          >
            <div className="flex items-start gap-2.5">
              <Icon size={16} className="mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">{t.title}</p>
                {t.message && <p className="mt-0.5 text-xs leading-relaxed text-slate-400">{t.message}</p>}
              </div>
              <button
                onClick={() => dismissToast(t.id)}
                className="rounded p-1 text-slate-500 transition hover:text-white"
                aria-label="Dismiss notification"
              >
                <X size={13} />
              </button>
            </div>
          </div>
        )
      })}
    </div>
  )
}
