/**
 * API client.
 *
 * - Uses VITE_API_URL when configured, otherwise same-origin (/api) which the
 *   Vite dev server proxies to FastAPI.
 * - Every call has a hard timeout so the UI never hangs.
 * - Failures throw an ApiError with `offline` set for network-level problems,
 *   letting the app switch to bundled fallback data.
 * - Auth: the short-lived access token lives in memory only; the refresh
 *   token is an HttpOnly cookie owned by the browser. On a 401 the client
 *   transparently refreshes once and replays the request; if the session is
 *   really gone it emits `AUTH_EXPIRED_EVENT` so the router can send the
 *   operator to the login screen.
 */

const RAW_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
const DEFAULT_TIMEOUT = 9000

export const AUTH_EXPIRED_EVENT = 'cybverse:session-expired'

let accessToken = null
let refreshPromise = null

export function setAccessToken(token) {
  accessToken = token || null
}

export function getAccessToken() {
  return accessToken
}

export class ApiError extends Error {
  constructor(message, { status = 0, offline = false, payload = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.offline = offline
    this.payload = payload
  }
}

function emitExpired() {
  accessToken = null
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
  }
}

/** Exchange the HttpOnly refresh cookie for a new access token (single-flight). */
export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const res = await fetch(`${RAW_BASE}/api/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) return null
      const data = await res.json().catch(() => null)
      if (data && data.access_token) {
        accessToken = data.access_token
        return data
      }
      return null
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

async function request(path, { method = 'GET', body = null, timeout = DEFAULT_TIMEOUT, __retried = false } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  let response
  try {
    response = await fetch(`${RAW_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
      signal: controller.signal,
    })
  } catch (err) {
    throw new ApiError(
      err && err.name === 'AbortError'
        ? `Request timed out: ${path}`
        : `Backend unreachable: ${path}`,
      { offline: true },
    )
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) {
    // Expired access token -> refresh once, then replay the original call.
    if (response.status === 401 && !__retried && !path.startsWith('/api/auth/')) {
      const refreshed = await refreshSession().catch(() => null)
      if (refreshed) {
        return request(path, { method, body, timeout, __retried: true })
      }
      emitExpired()
    }

    let payload = null
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
    const message =
      (payload && (payload.detail?.[0]?.msg || payload.detail)) ||
      `${method} ${path} failed with status ${response.status}`
    throw new ApiError(String(message), { status: response.status, payload })
  }

  try {
    return await response.json()
  } catch {
    throw new ApiError(`Invalid JSON from ${path}`, { status: response.status })
  }
}

export const api = {
  health: () => request('/api/health', { timeout: 4000 }),
  settings: () => request('/api/settings', { timeout: 4000 }),
  dashboard: () => request('/api/dashboard'),
  network: () => request('/api/network'),
  events: (limit = 120, offset = 0, eventType = '') =>
    request(`/api/events?limit=${limit}&offset=${offset}${eventType ? `&event_type=${eventType}` : ''}`),
  threats: (limit = 50) => request(`/api/threats?limit=${limit}`),
  incidents: (status = '') => request(`/api/incidents${status ? `?status=${status}` : ''}`),
  incident: (id) => request(`/api/incidents/${encodeURIComponent(id)}`),
  setIncidentStatus: (id, status) =>
    request(`/api/incidents/${encodeURIComponent(id)}/status`, {
      method: 'PATCH',
      body: { status },
    }),
  contain: (id) => request(`/api/incidents/${encodeURIComponent(id)}/contain`, { method: 'POST' }),
  attackGraphs: () => request('/api/attack-graph'),
  attackGraph: (id) => request(`/api/attack-graph/${encodeURIComponent(id)}`),
  scenarios: () => request('/api/scenarios'),
  simulate: (scenario, { intensity = 'normal', target = '' } = {}) =>
    request(`/api/simulate/${scenario}`, { method: 'POST', body: { intensity, target, replay: true }, timeout: 20000 }),
  analyze: (incidentId, question = '') =>
    request('/api/analyze', { method: 'POST', body: { incident_id: incidentId, question }, timeout: 20000 }),
  report: (incidentId) => request(`/api/reports/${encodeURIComponent(incidentId)}`, { timeout: 20000 }),
  demoStatus: () => request('/api/demo', { timeout: 4000 }),
  demoStart: () => request('/api/demo/start', { method: 'POST' }),
  demoReset: () => request('/api/demo/reset', { method: 'POST' }),
  demoStop: () => request('/api/demo/stop', { method: 'POST' }),
  resetSandbox: () => request('/api/reset', { method: 'POST' }),

  // ------------------------------------------------------------------ auth
  login: (email, password) => request('/api/auth/login', { method: 'POST', body: { email, password }, timeout: 8000 }),
  logout: () => request('/api/auth/logout', { method: 'POST', timeout: 6000 }),
  me: () => request('/api/auth/me'),
  changePassword: (current_password, new_password) =>
    request('/api/auth/password', { method: 'POST', body: { current_password, new_password } }),
  users: () => request('/api/auth/users'),
  createUser: (payload) => request('/api/auth/users', { method: 'POST', body: payload }),
  updateUser: (id, payload) => request(`/api/auth/users/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload }),
  deleteUser: (id) => request(`/api/auth/users/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  audit: (limit = 100) => request(`/api/audit?limit=${limit}`),
}

/** Run a request, returning `fallback` instead of throwing when offline. */
export async function withFallback(fn, fallback) {
  try {
    return { data: await fn(), offline: false, error: null }
  } catch (err) {
    return { data: fallback, offline: true, error: err instanceof ApiError ? err.message : String(err) }
  }
}

export const apiBase = RAW_BASE
