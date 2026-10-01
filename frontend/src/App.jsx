import React, { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import CommandCenterLayout from './layouts/CommandCenterLayout'
import Landing from './pages/Landing'
import PageLoader from './components/PageLoader'

const Overview = lazy(() => import('./pages/Overview'))
const Network3D = lazy(() => import('./pages/Network3D'))
const Threats = lazy(() => import('./pages/Threats'))
const AttackGraph = lazy(() => import('./pages/AttackGraph'))
const AIAnalyst = lazy(() => import('./pages/AIAnalyst'))
const Simulator = lazy(() => import('./pages/Simulator'))
const Incidents = lazy(() => import('./pages/Incidents'))
const IncidentDetail = lazy(() => import('./pages/IncidentDetail'))
const Reports = lazy(() => import('./pages/Reports'))
const Settings = lazy(() => import('./pages/Settings'))

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<CommandCenterLayout />}>
          <Route index element={<Overview />} />
          <Route path="network" element={<Network3D />} />
          <Route path="threats" element={<Threats />} />
          <Route path="attack-graph" element={<AttackGraph />} />
          <Route path="ai-analyst" element={<AIAnalyst />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="incidents/:id" element={<IncidentDetail />} />
          <Route path="reports" element={<Reports />} />
          <Route path="reports/:id" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
