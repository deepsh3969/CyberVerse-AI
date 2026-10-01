import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import {
  api,
  AUTH_EXPIRED_EVENT,
  refreshSession,
  setAccessToken,
} from '../services/api'

const WRITE_ROLES = ['analyst', 'admin']

/**
 * Default value when no <AuthProvider> is mounted (isolated component tests,
 * Storybook-style usage): behave exactly like an auth-disabled demo build.
 */
export const DEMO_AUTH = {
  user: null,
  authEnabled: false,
  ready: true,
  login: async () => {
    throw new Error('AuthProvider is not mounted')
  },
  logout: async () => {},
  authenticated: false,
  role: null,
  canWrite: true,
  isAdmin: true,
}

const AuthContext = createContext(DEMO_AUTH)

/**
 * Authentication state for the console.
 *
 * - `authEnabled === null`  : still discovering (show the page loader)
 * - `authEnabled === false` : demo deployment, everything stays open
 * - `authEnabled === true`  : `/app` requires a signed-in operator
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [authEnabled, setAuthEnabled] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    const bootstrap = async () => {
      try {
        const settings = await api.settings()
        if (cancelled) return
        const enabled = Boolean(settings && settings.auth_enabled)
        setAuthEnabled(enabled)
        if (enabled) {
          // The HttpOnly refresh cookie restores the session after a reload.
          const session = await refreshSession().catch(() => null)
          if (!cancelled && session && session.user) setUser(session.user)
        }
      } catch {
        // Backend unreachable or demo mode: never lock the console out.
        if (!cancelled) setAuthEnabled(false)
      } finally {
        if (!cancelled) setReady(true)
      }
    }

    const onExpired = () => setUser(null)
    bootstrap()
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    return () => {
      cancelled = true
      window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const result = await api.login(email, password)
    setAccessToken(result.access_token)
    setUser(result.user)
    setAuthEnabled(true)
    return result.user
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.logout()
    } catch {
      // logging out locally matters even if the network call fails
    }
    setAccessToken(null)
    setUser(null)
  }, [])

  const value = useMemo(() => {
    const authenticated = Boolean(user)
    return {
      user,
      authEnabled,
      ready,
      login,
      logout,
      authenticated,
      role: user ? user.role : null,
      canWrite: !authEnabled || (authenticated && WRITE_ROLES.includes(user.role)),
      isAdmin: !authEnabled || (authenticated && user.role === 'admin'),
    }
  }, [user, authEnabled, ready, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

export default AuthContext
