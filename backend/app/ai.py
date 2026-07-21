"""Lightweight anomaly detection → downtime-risk score (the "KI" module).

Not a heavy model: an IsolationForest is fitted on a rolling window of recent
running-tick features (cycle time, reject count). The anomaly score of the
latest tick is mapped to a 0-100 % downtime risk. Rising cycle times or reject
clusters — the usual precursors of a stoppage — push the score up.

Before enough samples are collected, a transparent heuristic is used so the
dashboard always has a value.
"""

from collections import deque

import numpy as np
from sklearn.ensemble import IsolationForest

from .config import IDEAL_CYCLE_MS


class DowntimeRiskModel:
    def __init__(self, window: int = 240, min_samples: int = 40, refit_every: int = 20):
        self._buf: deque[list[float]] = deque(maxlen=window)
        self._min_samples = min_samples
        self._refit_every = refit_every
        self._since_fit = 0
        self._model: IsolationForest | None = None

    def _heuristic(self, cycle_ms: float, rejects: int) -> float:
        cycle_penalty = max(0.0, (cycle_ms - IDEAL_CYCLE_MS) / IDEAL_CYCLE_MS)  # 0..~0.25+
        return float(min(100.0, 100.0 * (0.6 * cycle_penalty + 0.4 * min(1.0, rejects / 2.0))))

    def update(self, cycle_ms: float, rejects: int) -> float:
        """Add the latest running-tick features and return downtime risk in %."""
        feat = [float(cycle_ms), float(rejects)]
        self._buf.append(feat)
        self._since_fit += 1

        if len(self._buf) < self._min_samples:
            return round(self._heuristic(cycle_ms, rejects), 1)

        if self._model is None or self._since_fit >= self._refit_every:
            self._model = IsolationForest(n_estimators=80, contamination=0.08,
                                          random_state=42)
            self._model.fit(np.array(self._buf))
            self._since_fit = 0

        # decision_function: higher = more normal. Flip and squash to 0..100.
        score = float(self._model.decision_function(np.array([feat]))[0])
        risk = 100.0 / (1.0 + np.exp(12.0 * score))  # logistic on the raw score
        return round(float(risk), 1)
