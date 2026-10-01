import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError } from '../services/api'
import { loadPrefs, playTone, savePrefs } from '../utils/prefs'
import {
  FALLBACK_DASHBOARD,
  FALLBACK_DEMO,
  FALLBACK_EVENTS,
  FALLBACK_INCIDENTS,
  FALLBACK_NETWORK,
  FALLBACK_SCENARIOS,
  FALLBACK_SETTINGS,
} from '../data/demoData'

const AppContext = createContext(null)

let toastSeq = 0

export function AppProvider({ children }) {
  const [online, setOnline] = useState(null) // null = checking, true, false
  const [health, setHealth] = useState(null)
  const [settings, setSettings] = useState(FALLBACK_SETTINGS)
  const [dashboard, setDashboard] = useState(FALLBACK_DASHBOARD)
  const [network, setNetwork] = useState(FALLBACK_NETWORK)
  const [incidents, setIncidents] = useState(FALLBACK_INCIDENTS)
  const [threats, setThreats] = useState([])
  const [events, setEvents] = useState(FALLBACK_EVENTS)
  const [scenarios, setScenarios] = useState(FALLBACK_SCENARIOS)
  const [demo, setDemo] = useState(FALLBACK_DEMO)
  const [loading, setLoading] = useState(true)
  const [lastError, setLastError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const [toasts, setToasts] = useState([])
  const [prefs, setPrefsState] = useState(() => loadPrefs())
  const onlineRef = useRef(true)
  const threatCountRef = useRef(0)

  const setPrefs = useCallback((patch) => {
    setPrefsState((prev) => {
      const next = { ...prev, ...patch }
      savePrefs(next)
      return next
    })
  }, [])

  // alert tone when the detection engine produces a new threat
  useEffect(() => {
    const prev = threatCountRef.current
    if (threats.length > prev && prev !== 0 && prefs.sound) playTone('alert')
    threatCountRef.current = threats.length
  }, [threats, prefs.sound])

  // apply theme attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', prefs.theme || 'command')
  }, [prefs.theme])

  const pushToast = useCallback((toast) => {
    const id = (toastSeq += 1)
    setToasts((prev) => [...prev, { id, ...toast }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, toast.duration || 5200)
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const goOffline = useCallback(
    (reason) => {
      onlineRef.current = false
      setOnline(false)
      setDashboard(FALLBACK_DASHBOARD)
      setNetwork(FALLBACK_NETWORK)
      setIncidents(FALLBACK_INCIDENTS)
      setEvents(FALLBACK_EVENTS)
      setScenarios(FALLBACK_SCENARIOS)
      setDemo(FALLBACK_DEMO)
      setSettings(FALLBACK_SETTINGS)
      setLastError(reason || 'Backend unreachable')
    },
    [],
  )

  const refresh = useCallback(async () => {
    const calls = await Promise.allSettled([
      api.dashboard(),
      api.network(),
      api.incidents(),
      api.threats(60),
      api.events(140),
      api.scenarios(),
      api.demoStatus(),
      api.settings(),
    ])

    const [d, n, i, t, e, s, dm, st] = calls

    if (d.status === 'rejected') {
      const err = d.reason
      if (err instanceof ApiError && err.offline) {
        goOffline(err.message)
        setLoading(false)
        return
      }
      setLastError(err?.message || 'Failed to load dashboard')
    } else {
      onlineRef.current = true
      setOnline(true)
      setLastError(null)
      setDashboard(d.value)
      if (n.status === 'fulfilled') setNetwork(n.value)
      if (i.status === 'fulfilled') setIncidents(i.value.items)
      if (t.status === 'fulfilled') setThreats(t.value.items)
      if (e.status === 'fulfilled') setEvents(e.value.items)
      if (s.status === 'fulfilled') setScenarios(s.value.items)
      if (dm.status === 'fulfilled') setDemo(dm.value)
      if (st.status === 'fulfilled') setSettings(st.value)
      setUpdatedAt(Date.now())
    }
    setLoading(false)
  }, [goOffline])

  const checkHealth = useCallback(async () => {
    try {
      const h = await api.health()
      setHealth(h)
      setOnline(true)
      onlineRef.current = true
      return true
    } catch (err) {
      setHealth(null)
      if (err instanceof ApiError && err.offline) {
        setOnline((prev) => {
          if (prev !== false) goOffline(err.message)
          return false
        })
      } else {
        setLastError(err?.message || 'Health check failed')
      }
      return false
    }
  }, [goOffline])

  // boot + polling loop
  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      const alive = await checkHealth()
      if (!cancelled && alive) await refresh()
      else if (!cancelled && !alive) setLoading(false)
    }
    boot()
    const interval = Math.max(1500, Number(prefs.refreshInterval) || 4000)
    const id = setInterval(async () => {
      if (document.hidden) return
      await checkHealth()
      if (onlineRef.current) await refresh()
    }, interval)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [checkHealth, refresh, prefs.refreshInterval])

  // ------------------------------------------------------------------ actions
  const run = useCallback(
    async (fn, { success, fail, onSuccess, silentError = false } = {}) => {
      try {
        const result = await fn()
        if (success) pushToast({ type: 'success', title: success.title, message: success.message })
        await refresh()
        if (onSuccess) onSuccess(result)
        return { ok: true, data: result }
      } catch (err) {
        const message = err instanceof ApiError ? err.message : String(err)
        if (!silentError) {
          pushToast({ type: 'error', title: fail?.title || 'Request failed', message })
        }
        return { ok: false, error: message }
      }
    },
    [pushToast, refresh],
  )

  const actions = useMemo(
    () => ({
      simulate: (scenario, opts) =>
        run(() => api.simulate(scenario, opts), {
          success: { title: 'Simulation complete', message: `${scenario} events fed through the detection engine.` },
          fail: { title: 'Simulation failed' },
        }),
      contain: (incidentId) =>
        run(() => api.contain(incidentId), {
          success: { title: 'THREAT CONTAINED', message: 'Simulated containment actions applied to the sandbox.' },
          fail: { title: 'Containment failed' },
        }),
      setIncidentStatus: (incidentId, status) =>
        run(() => api.setIncidentStatus(incidentId, status), {
          success: { title: 'Status updated', message: `Incident marked ${status}.` },
          fail: { title: 'Update failed' },
        }),
      analyze: (incidentId, question) =>
        run(() => api.analyze(incidentId, question), {
          fail: { title: 'Analysis failed' },
          silentError: false,
        }),
      startDemo: () =>
        run(() => api.demoStart(), {
          success: { title: 'Demo started', message: 'Scripted attack scenario is now running.' },
          fail: { title: 'Could not start demo' },
        }),
      resetDemo: () =>
        run(() => api.demoReset(), {
          success: { title: 'Demo reset', message: 'Sandbox restored to baseline state.' },
          fail: { title: 'Reset failed' },
        }),
      stopDemo: () => run(() => api.demoStop(), { fail: { title: 'Stop failed' } }),
      resetSandbox: () =>
        run(() => api.resetSandbox(), {
          success: { title: 'Sandbox reset', message: 'All simulated telemetry cleared.' },
          fail: { title: 'Reset failed' },
        }),
      refresh,
      checkHealth,
    }),
    [run, refresh, checkHealth],
  )

  const value = useMemo(
    () => ({
      online,
      health,
      settings,
      dashboard,
      network,
      incidents,
      threats,
      events,
      scenarios,
      demo,
      loading,
      lastError,
      updatedAt,
      toasts,
      pushToast,
      dismissToast,
      actions,
      offline: online === false,
      prefs,
      setPrefs,
    }),
    [
      online,
      health,
      settings,
      dashboard,
      network,
      incidents,
      threats,
      events,
      scenarios,
      demo,
      loading,
      lastError,
      updatedAt,
      toasts,
      pushToast,
      dismissToast,
      actions,
      prefs,
      setPrefs,
    ],
  )

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
  return ctx
}

export default AppContext
