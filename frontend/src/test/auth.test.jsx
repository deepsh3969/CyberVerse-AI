import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { AuthProvider, useAuth, DEMO_AUTH } from '../context/AuthContext'
import { RequireAuth } from '../App'
import Login from '../pages/Login'
import { api, setAccessToken, getAccessToken, AUTH_EXPIRED_EVENT, refreshSession } from '../services/api'

const ADMIN = { id: 'USR-1', email: 'admin@cyberverse.local', role: 'admin', full_name: 'Admin', is_active: true }

function routes(authEnabled) {
  return {
    '/api/settings': { app: 'CyberVerse AI', auth_enabled: authEnabled },
    '/api/auth/refresh': { access_token: 'fresh-token', token_type: 'bearer', expires_in: 900, user: ADMIN },
    '/api/auth/login': { access_token: 'login-token', token_type: 'bearer', expires_in: 900, user: ADMIN },
    '/api/dashboard': { security_score: 90 },
  }
}

/** fetch mock with per-path overrides and call logging. */
function mockFetch({ paths = {}, dashboard401 = 0, refreshStatus = 200 } = {}) {
  const state = { refreshStatus, dashboards: 0 }
  const base = routes(false)
  const mock = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]
    const method = (options.method || 'GET').toUpperCase()
    if (path === '/api/auth/refresh' && method === 'POST') {
      return {
        ok: state.refreshStatus === 200,
        status: state.refreshStatus,
        json: async () =>
          state.refreshStatus === 200 ? routes(true)['/api/auth/refresh'] : { detail: 'Refresh token revoked or expired' },
      }
    }
    if (path === '/api/auth/login' && method === 'POST') {
      const body = JSON.parse(options.body || '{}')
      if (body.password !== 'AdminPass123!') {
        return { ok: false, status: 401, json: async () => ({ detail: 'Invalid email or password' }) }
      }
      return { ok: true, status: 200, json: async () => routes(true)['/api/auth/login'] }
    }
    if (path === '/api/auth/logout' && method === 'POST') {
      return { ok: true, status: 200, json: async () => ({ status: 'ok' }) }
    }
    if (path === '/api/dashboard') {
      state.dashboards += 1
      if (state.dashboards <= dashboard401) {
        return { ok: false, status: 401, json: async () => ({ detail: 'Authentication required' }) }
      }
      return { ok: true, status: 200, json: async () => base['/api/dashboard'] }
    }
    const table = { ...base, ...paths }
    if (table[path]) return { ok: true, status: 200, json: async () => table[path] }
    return { ok: false, status: 404, json: async () => ({ detail: 'not found' }) }
  })
  global.fetch = mock
  return { fetchMock: mock, state }
}

function Console() {
  const { canWrite, isAdmin } = useAuth()
  return <div data-testid="console" data-can-write={String(canWrite)} data-is-admin={String(isAdmin)} />
}

function LoginPage() {
  return <div data-testid="login-page" />
}

function renderGuard(overrides = {}) {
  const handle = mockFetch(overrides)
  const utils = render(
    <MemoryRouter initialEntries={['/app']}>
      <AuthProvider>
        <Routes>
          <Route
            path="/app"
            element={
              <RequireAuth>
                <Console />
              </RequireAuth>
            }
          />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
  return { ...utils, ...handle }
}

beforeEach(() => {
  setAccessToken(null)
})

afterEach(() => {
  setAccessToken(null)
  vi.restoreAllMocks()
})

describe('RequireAuth', () => {
  it('lets everyone in when the deployment has auth disabled', async () => {
    renderGuard()
    await waitFor(() => expect(screen.getByTestId('console')).toBeInTheDocument())
    expect(screen.getByTestId('console')).toHaveAttribute('data-can-write', 'true')
    expect(screen.getByTestId('console')).toHaveAttribute('data-is-admin', 'true')
  })

  it('redirects unauthenticated visitors to /login when auth is on', async () => {
    renderGuard({ refreshStatus: 401, paths: { '/api/settings': routes(true)['/api/settings'] } })
    await waitFor(() => expect(screen.getByTestId('login-page')).toBeInTheDocument())
    expect(screen.queryByTestId('console')).not.toBeInTheDocument()
  })

  it('restores the session from the refresh cookie', async () => {
    renderGuard({ paths: { '/api/settings': routes(true)['/api/settings'] } })
    await waitFor(() => expect(screen.getByTestId('console')).toBeInTheDocument())
    expect(getAccessToken()).toBe('fresh-token')
    expect(screen.getByTestId('console')).toHaveAttribute('data-is-admin', 'true')
  })
})

describe('Login page', () => {
  async function renderLogin() {
    const handle = mockFetch({ refreshStatus: 401, paths: { '/api/settings': routes(true)['/api/settings'] } })
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/app"
              element={
                <RequireAuth>
                  <Console />
                </RequireAuth>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())
    return handle
  }

  it('shows the backend error for bad credentials', async () => {
    await renderLogin()
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@cyberverse.local' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password'))
    expect(screen.queryByTestId('console')).not.toBeInTheDocument()
  })

  it('signs in and enters the console', async () => {
    await renderLogin()
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'admin@cyberverse.local' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'AdminPass123!' } })
    fireEvent.click(screen.getByRole('button', { name: /Sign in/i }))
    await waitFor(() => expect(screen.getByTestId('console')).toBeInTheDocument())
    expect(getAccessToken()).toBe('login-token')
  })
})

describe('API client session handling', () => {
  it('refreshes once and replays the request after a 401', async () => {
    const handle = mockFetch({ dashboard401: 1, paths: { '/api/settings': routes(true)['/api/settings'] } })
    const data = await api.dashboard()
    expect(data.security_score).toBe(90)
    expect(getAccessToken()).toBe('fresh-token')
    const paths = handle.fetchMock.mock.calls.map(([url]) => String(url))
    expect(paths.filter((p) => p.includes('/api/dashboard')).length).toBe(2)
    expect(paths.some((p) => p.includes('/api/auth/refresh'))).toBe(true)
  })

  it('emits the session-expired event when refresh fails', async () => {
    mockFetch({ dashboard401: 1, refreshStatus: 401, paths: { '/api/settings': routes(true)['/api/settings'] } })
    const expired = vi.fn()
    window.addEventListener(AUTH_EXPIRED_EVENT, expired, { once: true })
    const err = await api.dashboard().catch((e) => e)
    expect(err.status).toBe(401)
    expect(expired).toHaveBeenCalledTimes(1)
    expect(getAccessToken()).toBeNull()
    window.removeEventListener(AUTH_EXPIRED_EVENT, expired)
  })

  it('refreshSession returns null on a rejected cookie', async () => {
    const { state } = mockFetch({ paths: { '/api/settings': routes(true)['/api/settings'] } })
    state.refreshStatus = 401
    const result = await refreshSession()
    expect(result).toBeNull()
  })
})

describe('DEMO_AUTH fallback', () => {
  it('keeps isolated components open (no provider mounted)', () => {
    expect(DEMO_AUTH.authEnabled).toBe(false)
    expect(DEMO_AUTH.canWrite).toBe(true)
    expect(DEMO_AUTH.ready).toBe(true)
  })
})
