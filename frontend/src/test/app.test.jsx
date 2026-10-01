import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { AppProvider } from '../context/AppContext'
import Overview from '../pages/Overview'
import Threats from '../pages/Threats'
import Simulator from '../pages/Simulator'
import Landing from '../pages/Landing'
import {
  FALLBACK_DASHBOARD,
  FALLBACK_EVENTS,
  FALLBACK_INCIDENTS,
  FALLBACK_NETWORK,
  FALLBACK_SCENARIOS,
} from '../data/demoData'

// WebGL is unavailable in jsdom, so the 3D scenes are stubbed out.
vi.mock('../three/HeroScene', () => ({ default: () => <div data-testid="hero-scene" /> }))
vi.mock('../three/NetworkScene', () => ({ default: () => <div data-testid="network-scene" /> }))

const ROUTES = {
  '/api/health': {
    status: 'ok',
    version: '1.0.0',
    database: 'disabled',
    ai_provider: 'local-analysis-engine',
    ml_backend: 'isolation-forest',
    uptime_seconds: 12,
  },
  '/api/dashboard': FALLBACK_DASHBOARD,
  '/api/network': FALLBACK_NETWORK,
  '/api/incidents': { items: FALLBACK_INCIDENTS, total: FALLBACK_INCIDENTS.length },
  '/api/threats': {
    items: [
      {
        id: 'THR-TEST01',
        threat_type: 'Brute Force',
        severity: 'HIGH',
        risk_score: 91,
        confidence: 0.94,
        anomaly_score: 0.83,
        affected_asset: 'Authentication Server',
        source: '203.0.113.44',
        destination: 'auth',
        timestamp: Date.now() / 1000,
        evidence: ['38 failed login attempts', 'Successful login after repeated failures'],
        detector: 'isolation-forest + rules',
        status: 'ACTIVE',
      },
    ],
    total: 1,
  },
  '/api/events': { items: FALLBACK_EVENTS, total: FALLBACK_EVENTS.length, analyzed: 12842 },
  '/api/scenarios': { items: FALLBACK_SCENARIOS },
  '/api/demo': { state: 'idle', step: -1, label: '', detail: '', steps: [] },
  '/api/settings': { app: 'CyberVerse AI', ai_provider: 'local-analysis-engine', ml_backend: 'isolation-forest' },
}

function installFetchMock() {
  const mock = vi.fn(async (url) => {
    const path = String(url).split('?')[0]
    if (path.startsWith('/api/simulate/')) {
      const scenario = path.split('/').pop()
      return {
        ok: true,
        status: 200,
        json: async () => ({
          scenario,
          events: FALLBACK_EVENTS.slice(0, 4),
          threats: ROUTES['/api/threats'].items,
          incident: FALLBACK_INCIDENTS[0],
          attack_graph: null,
          message: 'synthetic sequence generated',
        }),
      }
    }
    const key = Object.keys(ROUTES).find((k) => path === k || path.startsWith(`${k}/`))
    if (!key) {
      return { ok: false, status: 404, json: async () => ({ detail: 'not found' }) }
    }
    return { ok: true, status: 200, json: async () => ROUTES[key] }
  })
  global.fetch = mock
  return mock
}

function renderWithProviders(ui, route = '/app') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AppProvider>{ui}</AppProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  installFetchMock()
})

describe('Landing page', () => {
  it('renders hero copy and both CTAs', async () => {
    renderWithProviders(<Landing />, '/')
    expect(screen.getAllByText(/CYBERVERSE/i).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Enter Command Center/i }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: /Run Demo/i }).length).toBeGreaterThan(0)
  })
})

describe('Overview dashboard', () => {
  it('renders KPI tiles and charts from API data', async () => {
    renderWithProviders(<Overview />)
    await waitFor(() => expect(screen.getByText('AI Security Score')).toBeInTheDocument())
    expect(screen.getByText('93 / 100')).toBeInTheDocument()
    expect(screen.getByText('Active Incidents')).toBeInTheDocument()
    expect(screen.getByText('Events Analyzed')).toBeInTheDocument()
    expect(screen.getByText('Threats Blocked')).toBeInTheDocument()
    expect(screen.getByText('Protected Assets')).toBeInTheDocument()
    expect(screen.getByText('Threats over time')).toBeInTheDocument()
    expect(screen.getByText('Recent detections')).toBeInTheDocument()
  })

  it('shows the operational storyline', async () => {
    renderWithProviders(<Overview />)
    await waitFor(() => expect(screen.getByText('Operational storyline')).toBeInTheDocument())
    expect(screen.getByText('CONTAINMENT')).toBeInTheDocument()
  })
})

describe('Threat cards', () => {
  it('renders detected threats with evidence', async () => {
    renderWithProviders(<Threats />)
    await waitFor(() => expect(screen.getByText('Brute Force')).toBeInTheDocument())
    expect(screen.getByText(/38 failed login attempts/)).toBeInTheDocument()
    expect(screen.getByText(/confidence 94%/)).toBeInTheDocument()
  })
})

describe('Simulator buttons', () => {
  it('lists all eight scenarios', async () => {
    renderWithProviders(<Simulator />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Simulate Attack/i })).toHaveLength(8))
  })

  it('calls the simulation endpoint when clicked', async () => {
    const fetchMock = global.fetch
    renderWithProviders(<Simulator />)
    await waitFor(() => expect(screen.getAllByRole('button', { name: /Simulate Attack/i })).toHaveLength(8))
    fireEvent.click(screen.getAllByRole('button', { name: /Simulate Attack/i })[1])
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/simulate/brute-force'),
        expect.objectContaining({ method: 'POST' }),
      ),
    )
  })
})
