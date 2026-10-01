import React, { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ShieldAlert } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import PageLoader from '../components/PageLoader'

export default function Login() {
  const { authEnabled, ready, authenticated, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (!ready) return <PageLoader />

  // Demo deployment (auth off): nothing to sign in to.
  if (authEnabled === false) return <Navigate to="/" replace />

  if (authenticated) {
    const from = location.state?.from || '/app'
    return <Navigate to={from} replace />
  }

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(email.trim(), password)
      navigate(location.state?.from || '/app', { replace: true })
    } catch (err) {
      setError(err && err.message ? err.message : 'Sign in failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-4">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-6 flex items-center justify-center gap-2.5" aria-label="Back to landing page">
          <span className="grid h-9 w-9 place-items-center rounded-md border border-cyber-400/40 bg-cyber-400/10">
            <ShieldAlert size={18} className="text-cyber-400" />
          </span>
          <span className="text-sm font-semibold tracking-[0.2em] text-white">CYBERVERSE AI</span>
        </Link>

        <form
          onSubmit={submit}
          className="rounded-xl border border-white/[0.07] bg-white/[0.03] p-6 shadow-card backdrop-blur-sm"
        >
          <p className="label-caps">Restricted console</p>
          <h1 className="mt-1 text-lg font-semibold text-white">Operator sign in</h1>
          <p className="mt-1 text-[12.5px] text-slate-500">
            Authentication is required for this deployment. Analysts can run and contain simulations; admins manage
            users and the audit trail.
          </p>

          <label className="mt-5 block text-[12px] text-slate-400" htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input mt-1.5"
            placeholder="analyst@company.com"
          />

          <label className="mt-4 block text-[12px] text-slate-400" htmlFor="login-password">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input mt-1.5"
            placeholder="••••••••"
          />

          {error && (
            <p role="alert" className="mt-4 rounded-lg border border-alert-500/30 bg-alert-500/10 px-3 py-2 text-[12.5px] text-alert-400">
              {error}
            </p>
          )}

          <button type="submit" className="btn-primary mt-5 w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 text-center text-[11.5px] text-slate-600">
          Sessions are short-lived; the browser silently refreshes them while you work.
        </p>
      </div>
    </div>
  )
}
