"""State-dependent lifecycle allocation rules."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LifecycleState:
    """State passed into a lifecycle allocation policy."""

    scenario_index: int
    year_index: int
    age: int
    years_to_retirement: int
    total_years: int
    capital: float
    real_capital: float
    target_real_capital: float
    funding_ratio: float


def default_state_policy(state: LifecycleState) -> np.ndarray:
    """
    Simple state-dependent policy for:
    Euro_State, Euro_ILBs, Equity_Hedged.

    The base glidepath reduces equity through time. A low funding ratio adds
    equity risk; a high funding ratio shifts weight toward defensive assets.
    """

    if state.total_years <= 0:
        progress = 1.0
    else:
        progress = 1.0 - state.years_to_retirement / state.total_years
    progress = float(np.clip(progress, 0.0, 1.0))

    equity = 0.65 * (1.0 - progress) + 0.25 * progress
    ilb = 0.20 * (1.0 - progress) + 0.45 * progress
    euro_state = 1.0 - equity - ilb

    if state.funding_ratio < 0.90:
        equity += 0.10
        ilb -= 0.05
        euro_state -= 0.05
    elif state.funding_ratio > 1.10:
        equity -= 0.10
        ilb += 0.05
        euro_state += 0.05

    return normalize_weights(np.array([euro_state, ilb, equity], dtype=float))


def normalize_weights(weights: np.ndarray) -> np.ndarray:
    """Clip negative weights to zero and normalize to sum to one."""

    weights = np.asarray(weights, dtype=float)
    if weights.ndim != 1:
        raise ValueError(f"weights must be one-dimensional, got {weights.shape}.")

    weights = np.clip(weights, 0.0, None)
    total = float(weights.sum())
    if total == 0.0:
        raise ValueError("Allocation policy returned all-zero weights.")
    return weights / total
