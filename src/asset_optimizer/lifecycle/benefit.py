"""Benefit valuation and CRRA helpers."""

from __future__ import annotations

import numpy as np


def present_value(discount_factors: np.ndarray, cashflow: np.ndarray | None = None) -> float | np.ndarray:
    """Discount a cashflow stream with the supplied discount factors."""

    discount_factors = np.asarray(discount_factors, dtype=float)
    if discount_factors.ndim not in (1, 2):
        raise ValueError(f"discount_factors must be one- or two-dimensional, got {discount_factors.shape}.")

    if cashflow is None:
        cashflow = np.ones_like(discount_factors, dtype=float)
    else:
        cashflow = np.asarray(cashflow, dtype=float)

    discount_factors, cashflow = np.broadcast_arrays(discount_factors, cashflow)

    if discount_factors.ndim == 1:
        return float(np.sum(discount_factors * cashflow))
    if discount_factors.ndim == 2:
        return np.sum(discount_factors * cashflow, axis=1)

    raise ValueError(f"discount_factors must be one- or two-dimensional, got {discount_factors.shape}.")


def bought_benefit(
    real_capital: float | np.ndarray,
    discount_factors: np.ndarray,
    cashflow: np.ndarray | None = None,
) -> float | np.ndarray:
    """Return the annuity-style benefit purchased by terminal real capital."""

    pv = present_value(discount_factors, cashflow=cashflow)
    if np.any(np.asarray(pv) <= 0.0):
        raise ValueError("Present value must be positive.")

    benefit = np.asarray(real_capital, dtype=float) / pv
    return float(benefit) if np.ndim(benefit) == 0 else benefit


def crra_utility(values: np.ndarray, gamma: float) -> np.ndarray:
    """CRRA utility for strictly positive values."""

    values = np.asarray(values, dtype=float)
    if np.any(values <= 0.0):
        raise ValueError("CRRA utility requires strictly positive values.")

    if gamma == 1.0:
        return np.log(values)

    return np.power(values, 1.0 - gamma) / (1.0 - gamma)


def certainty_equivalent(values: np.ndarray, gamma: float) -> float:
    """Return the CRRA certainty equivalent of a sample."""

    utility = crra_utility(values, gamma)
    mean_utility = float(np.mean(utility))

    if gamma == 1.0:
        return float(np.exp(mean_utility))

    transformed = (1.0 - gamma) * mean_utility
    if transformed <= 0.0:
        raise ValueError("Mean utility is incompatible with the requested gamma.")

    return float(np.power(transformed, 1.0 / (1.0 - gamma)))


def relative_certainty_equivalent(
    strategy_values: np.ndarray,
    benchmark_values: np.ndarray,
    gamma: float,
) -> float:
    """Return the CE improvement relative to the benchmark sample."""

    strategy_ce = certainty_equivalent(strategy_values, gamma)
    benchmark_ce = certainty_equivalent(benchmark_values, gamma)
    return float(strategy_ce / benchmark_ce - 1.0)


discounted_cashflow_pv = present_value
terminal_real_benefit = bought_benefit
crra_certainty_equivalent = certainty_equivalent
