# CyberVerse AI — Frontend

React + Vite console for the CyberVerse command center.

## Run

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api → 127.0.0.1:8000)
```

## Build / test

```bash
npm run build        # production bundle in dist/
npm run preview      # serve the production bundle
npm run test         # vitest + testing library
```

## Layout

```
src/
├── components/   # UI primitives, event console, demo controller, storyline ribbon
├── layouts/      # CommandCenterLayout (sidebar, topbar, offline banner, toasts)
├── pages/        # Landing, Overview, Network3D, Threats, AttackGraph,
│                 # AIAnalyst, Simulator, Incidents, IncidentDetail, Reports, Settings
├── charts/       # Recharts wrappers
├── three/        # NetworkScene (interactive) + HeroScene (landing)
├── context/      # AppContext: polling, actions, toasts, preferences
├── hooks/        # usePoll
├── services/     # api.js — fetch client with timeouts and offline fallback
├── data/         # demoData.js — bundled preview data when the API is offline
└── utils/        # formatting + preferences/alert tone helpers
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | Backend origin. Empty = same-origin `/api` (dev proxy). Set this in production. |
| `VITE_POLL_INTERVAL` | Reference polling cadence (ms) |

Runtime preferences (animation intensity, sound, theme, refresh interval, demo controls) are stored in
`localStorage` under `cyberverse.prefs` and never leave the browser.

## Offline behaviour

If the API cannot be reached the console shows a persistent banner and renders the bundled preview
dataset, so the interface remains explorable. Actions that require the backend stay disabled with
tooltips explaining why.
