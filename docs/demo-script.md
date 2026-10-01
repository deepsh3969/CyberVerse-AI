# Hackathon Demo Script (~2 minutes)

The demo is fully scripted and repeatable. Start with the landing page, then press one button.

## Before you start

```bash
# terminal 1
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
# terminal 2
cd frontend && npm run dev
```
Open http://localhost:5173 and confirm the header shows **LIVE** (green).

## The run

| Time | Screen | Say | Do |
| --- | --- | --- | --- |
| 0:00 | Landing | "Security teams see alerts, not stories. CyberVerse turns telemetry into a visible attack-to-containment narrative." | Point at the 8-stage storyline strip |
| 0:15 | Landing | "Everything below runs on synthetic telemetry in a sandbox — nothing touches a real network." | Click **ENTER COMMAND CENTER** |
| 0:25 | Overview | "This is the SOC: score, threat level, open cases, and five live charts." | Hover the KPI tiles and charts |
| 0:40 | Overview | "One button runs the whole story." | Click **START HACKATHON DEMO** |
| 0:45 | Overview | Walk the 12-step indicator: "baseline → recon → credential attack → detection" | Watch the event console fill |
| 1:00 | 3D Network | "Detection changes the infrastructure itself." | Open **3D Network** — red/yellow nodes, red attack edges, packets |
| 1:15 | Overview/Incidents | "The engine opened a case with evidence and a risk score." | Open the incident from the demo panel |
| 1:25 | Incident | "AI explains what happened, why it matters and what to do." | Show evidence, timeline, recommendations |
| 1:40 | Attack Graph | "Here is the path from attacker to crown-jewel data." | Click a hop → node details + AI assessment |
| 1:50 | Incident | "Analyst response is one click — and it is simulated." | Click **CONTAIN THREAT** → confirm |
| 2:00 | Overview | "Session terminated, path blocked, endpoint isolated — score recovers." | Show the THREAT CONTAINED banner and advancing storyline |
| 2:10 | Reports | "Every case exports as a PDF/HTML report." | Open **Reports** → EXPORT |

## Reset and run again

Overview → demo panel → **Reset**, or `curl -X POST http://localhost:8000/api/demo/reset`.

## Backup talking points

- **Detection is real ML**: 13 features per event, Isolation Forest trained locally, fused with an
  explainable rule engine; evidence lines come from both.
- **AI analyst works without keys** — the local engine produces the same structure; drop in `AI_API_KEY`
  and it switches providers.
- **Everything degrades gracefully**: unplug the backend and the console still renders preview data with a
  clear banner.
- **Defensive only**: no scanning, probing, exploiting or credential use outside this application.
