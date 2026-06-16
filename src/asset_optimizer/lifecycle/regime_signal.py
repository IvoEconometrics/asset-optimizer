"""Shared moving-average regime helpers."""

from __future__ import annotations

import numpy as np


NEUTRAL_REGIME = "neutraal"
HIGH_RATE_REGIME = "hoge_reele_rente"
LOW_RATE_REGIME = "lage_reele_rente"


def trailing_moving_average(values: np.ndarray, window_years: int) -> float:
    """Return the trailing moving average over the available history."""

    values = np.asarray(values, dtype=float)
    if values.ndim != 1:
        raise ValueError(f"values must be one-dimensional, got {values.shape}.")
    if values.size == 0:
        raise ValueError("values must contain at least one observation.")
    if window_years < 1:
        raise ValueError("window_years must be at least 1.")

    start_index = max(0, values.size - int(window_years))
    return float(np.mean(values[start_index:]))


def regime_from_rate_vs_ma(
    current_rate: float,
    moving_average: float,
    *,
    high_regime: str = HIGH_RATE_REGIME,
    low_regime: str = LOW_RATE_REGIME,
) -> str:
    """Map a current rate and moving average to one of the three regimes."""

    current_rate = float(current_rate)
    moving_average = float(moving_average)

    if current_rate > moving_average:
        return high_regime
    if current_rate < moving_average:
        return low_regime
    return NEUTRAL_REGIME
