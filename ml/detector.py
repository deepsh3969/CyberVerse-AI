"""Standalone anomaly scoring helper for the CyberVerse detection approach.

The production path lives in ``backend/app/ml/detector.py`` (rules + isolation
forest). This module exposes the same scoring idea as a tiny importable utility
for notebooks, experiments and the training script.

Usage:

    from ml.detector import IsolationScorer
    scorer = IsolationScorer()
    score = scorer.score(vector)      # 0.0 (normal) .. 1.0 (anomalous)
"""
from __future__ import annotations

import os
import sys
from typing import Iterable, Sequence

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
for _p in (REPO_ROOT, BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MODEL_PATH = os.path.join(REPO_ROOT, "ml", "models", "isolation_forest.joblib")

FEATURE_DIM = 13


class IsolationScorer:
    """Load the persisted isolation forest (training on first use if missing)."""

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        self.model_path = model_path
        self.model = None
        self.backend = "untrained"
        self._load()

    def _load(self) -> None:
        try:
            import joblib

            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.backend = f"joblib:{os.path.basename(self.model_path)}"
                return
        except Exception:
            pass
        self._train()

    def _train(self) -> None:
        from sklearn.ensemble import IsolationForest

        try:
            from app.ml.features import synthetic_normal_dataset

            data = synthetic_normal_dataset()
        except Exception:  # pragma: no cover - standalone use
            rng = np.random.default_rng(42)
            data = np.clip(rng.beta(2, 5, size=(2000, FEATURE_DIM)), 0, 1)
        self.model = IsolationForest(n_estimators=140, contamination=0.045, random_state=42, n_jobs=-1)
        self.model.fit(data)
        self.backend = "in-memory"

    def score(self, vector: Sequence[float]) -> float:
        arr = np.asarray(vector, dtype=np.float64).reshape(1, -1)
        decision = float(self.model.decision_function(arr)[0])
        return float(np.clip(0.5 - decision, 0.0, 1.0))

    def scores(self, vectors: Iterable[Sequence[float]]) -> list[float]:
        return [self.score(v) for v in vectors]

    def is_anomalous(self, vector: Sequence[float], threshold: float = 0.6) -> bool:
        return self.score(vector) >= threshold


if __name__ == "__main__":
    scorer = IsolationScorer()
    rng = np.random.default_rng(3)
    normal = np.clip(rng.beta(2, 5, size=FEATURE_DIM), 0, 1)
    attack = np.array([0.9, 0.95, 0.04, 0.85, 0.4, 0.3, 0.1, 0.1, 0.0, 1.0, 0.9, 0.6, 0.0])
    print(f"backend: {scorer.backend}")
    print(f"normal-vector score : {scorer.score(normal):.3f}")
    print(f"attack-vector score : {scorer.score(attack):.3f}")
