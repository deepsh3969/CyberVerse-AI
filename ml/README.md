# CyberVerse AI — ML

Local, download-free anomaly detection for synthetic security telemetry.

## Contents

| File | Purpose |
| --- | --- |
| `train.py` | Trains an Isolation Forest on a procedurally generated benign baseline, prints hold-out metrics, saves `models/isolation_forest.joblib` |
| `detector.py` | Small importable `IsolationScorer` used for notebooks/experiments |
| `data/baseline_sample.csv` | 150 sample baseline feature vectors (13 columns) |
| `models/` | Trained artifacts (git-ignored; regenerate any time) |

## Usage

```bash
# from the repository root, using the backend virtualenv
backend/.venv/bin/python ml/train.py          # Windows: backend\.venv\Scripts\python.exe ml/train.py
backend/.venv/bin/python ml/detector.py
```

Example output:

```
CyberVerse AI — isolation forest training
  benign samples   : 3000
  attack samples   : 400 (synthetic, for validation only)
  accuracy         : 0.960
  saved model      : ml/models/isolation_forest.joblib (1938.4 KB)
```

## Why Isolation Forest

- Unsupervised: no labelled attack dataset required.
- Trains in well under a second on a laptop CPU.
- No model weights are downloaded — the baseline is generated procedurally at startup.
- Scores are continuous, so they combine cleanly with explainable rules.

## Feature vector (13 dimensions)

`event_frequency · failed_login_count · avg_interval · source_frequency · destination_frequency ·
request_count · bytes_out · port_spread · hour_sin · hour_cos · asset_sensitivity · severity_code · rare_event`

## Production integration

`backend/app/ml/detector.py` fuses the model with a rule engine and is the code path used by the API.
The model file is optional: if missing, the backend retrains on startup.
