/**
 * API client.
 *
 * - Uses VITE_API_URL when configured, otherwise same-origin (/api) which the
 *   Vite dev server proxies to FastAPI.
 * - Every call has a hard timeout so the UI never hangs.
 * - Failures throw an ApiError with `offline` set for network-level problems,
 *   letting the app switch to bundled fallback data.
 */

const RAW_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
const DEFAULT_TIMEOUT = 9000

export class ApiError extends Error {
  constructor(message, { status = 0, offline = false, payload = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.offline = offline
    this.payload = payload
  }
}

async function request(path, { method = 'GET', body = null, timeout = DEFAULT_TIMEOUT } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeout)
  let response
  try {
    response = await fetch(`${RAW_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
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
