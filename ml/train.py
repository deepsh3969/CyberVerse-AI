"""Train the CyberVerse AI anomaly detector.

Runs entirely locally: synthesises a benign behavioural baseline, fits an
Isolation Forest, reports hold-out metrics and persists the model to
ml/models/isolation_forest.joblib.

Usage (from the repository root or backend/):

    python ml/train.py
    python ml/train.py --samples 4000 --contamination 0.05
"""
from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
for path in (REPO_ROOT, BACKEND_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import numpy as np  # noqa: E402
from sklearn.ensemble import IsolationForest  # noqa: E402
from sklearn.metrics import classification_report  # noqa: E402

try:
    from app.ml.features import synthetic_normal_dataset, cycle_encode
except ImportError:  # pragma: no cover - standalone fallback
    def cycle_encode(value, period):
        angle = 2 * np.pi * (value % period) / period
        return np.sin(angle), np.cos(angle)

    def synthetic_normal_dataset(n=2600, seed=42):
        rng = np.random.default_rng(seed)
        rows = []
        for _ in range(n):
            hour = rng.uniform(0, 24)
            s, c = cycle_encode(hour, 24.0)
            rows.append([
                min(rng.gamma(2.0, 0.06), 1.6),
                rng.beta(1.1, 14.0),
                rng.beta(5.0, 2.0),
                min(rng.gamma(2.2, 0.05), 1.5),
                min(rng.gamma(2.0, 0.05), 1.5),
                min(rng.gamma(1.8, 0.05), 1.4),
                rng.beta(1.4, 6.0),
                min(rng.beta(1.2, 8.0), 0.8),
                s,
                c,
                rng.beta(2.0, 3.0) * 0.9 + 0.05,
                rng.choice([0, 0, 0, 1, 1, 2]) / 4.0,
                0.0 if rng.random() > 0.04 else 1.0,
            ])
        return np.asarray(rows, dtype=np.float64)


def synthetic_attack_dataset(n: int = 400, seed: int = 7) -> np.ndarray:
    """Deliberately anomalous feature vectors used only for sanity metrics."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        kind = i % 4
        if kind == 0:  # credential burst
            row = [0.9, 0.95, 0.04, 0.85, 0.4, 0.3, 0.1, 0.1, 0.0, 1.0, 0.9, 0.6, 0.0]
        elif kind == 1:  # scan
            row = [0.8, 0.05, 0.02, 0.9, 0.6, 0.5, 0.2, 0.95, 0.3, 0.9, 0.4, 0.5, 1.0]
        elif kind == 2:  # bulk egress
            row = [0.5, 0.1, 0.3, 0.5, 0.9, 0.8, 0.97, 0.2, 0.7, 0.8, 1.0, 1.0, 0.0]
        else:  # off-hours insider
            row = [0.7, 0.2, 0.1, 0.6, 0.8, 0.9, 0.75, 0.3, -0.9, -0.4, 0.95, 0.8, 0.0]
        jitter = rng.normal(0, 0.03, size=13)
        rows.append(np.clip(np.array(row) + jitter, -1, 1))
    return np.asarray(rows, dtype=np.float64)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the CyberVerse isolation forest")
    parser.add_argument("--samples", type=int, default=3000, help="benign baseline samples")
    parser.add_argument("--contamination", type=float, default=0.045)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(REPO_ROOT, "ml", "models", "isolation_forest.joblib"),
        help="output path for the trained model",
    )
    args = parser.parse_args()

    benign = synthetic_normal_dataset(n=args.samples, seed=args.seed)
    attacks = synthetic_attack_dataset(n=400, seed=args.seed + 1)

    model = IsolationForest(
        n_estimators=160,
        contamination=args.contamination,
        random_state=args.seed,
        n_jobs=-1,
    )
    model.fit(benign)

    benign_scores = -model.decision_function(benign)
    attack_scores = -model.decision_function(attacks)
    threshold = float(np.percentile(benign_scores, (1 - args.contamination) * 100))
    y_true = np.concatenate([np.zeros(len(benign_scores)), np.ones(len(attack_scores))])
    y_pred = np.concatenate([(benign_scores > threshold).astype(int), (attack_scores > threshold).astype(int)])

    print("CyberVerse AI — isolation forest training")
    print(f"  benign samples   : {len(benign)}")
    print(f"  attack samples   : {len(attacks)} (synthetic, for validation only)")
    print(f"  threshold        : {threshold:.4f}")
    print(f"  benign mean/max  : {benign_scores.mean():.4f} / {benign_scores.max():.4f}")
    print(f"  attack mean/max  : {attack_scores.mean():.4f} / {attack_scores.max():.4f}")
    print(classification_report(y_true, y_pred, target_names=["benign", "attack"], digits=3))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    try:
        import joblib

        joblib.dump(model, args.out)
        size_kb = os.path.getsize(args.out) / 1024
        print(f"  saved model      : {args.out} ({size_kb:.1f} KB)")
    except Exception as exc:  # pragma: no cover
        print(f"  model not saved ({exc}) — the backend retrains at startup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
