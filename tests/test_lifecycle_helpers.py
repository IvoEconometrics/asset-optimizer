"""Regression tests for benefit valuation and moving-average regime helpers."""

import numpy as np
import pandas as pd

from asset_optimizer.lifecycle.benefit import (
    bought_benefit,
    certainty_equivalent,
    present_value,
    relative_certainty_equivalent,
)
from asset_optimizer.lifecycle.regime_signal import regime_from_rate_vs_ma, trailing_moving_average
from asset_optimizer.lifecycle.rule_based_lifecycle import rule_based_lifecycle
from asset_optimizer.lifecycle.us_backtest_rules import three_regime_lifecycle


def _lifecycle_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"lifecycle": "neutraal", "age": 30, "Euro_Staat": 0.5, "Euro_ILBs": 0.3, "Aandelen": 0.2},
            {"lifecycle": "hoge_reele_rente", "age": 30, "Euro_Staat": 0.7, "Euro_ILBs": 0.2, "Aandelen": 0.1},
            {"lifecycle": "lage_reele_rente", "age": 30, "Euro_Staat": 0.2, "Euro_ILBs": 0.3, "Aandelen": 0.5},
        ]
    )


def _backtest_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"lifecycle": "neutraal", "age": 30, "Bond_Return": 0.5, "ILB_Return": 0.3, "Equity_Return": 0.2},
            {"lifecycle": "hoge_reele_rente", "age": 30, "Bond_Return": 0.7, "ILB_Return": 0.2, "Equity_Return": 0.1},
            {"lifecycle": "lage_reele_rente", "age": 30, "Bond_Return": 0.2, "ILB_Return": 0.3, "Equity_Return": 0.5},
        ]
    )


def test_present_value_and_bought_benefit_use_discount_curve_placeholder_cashflow() -> None:
    discount_factors = np.array(
        [1.0, 0.975860357284546, 0.973425149917603],
        dtype=float,
    )

    pv = present_value(discount_factors)
    assert np.isclose(pv, discount_factors.sum())
    assert np.isclose(bought_benefit(294.9285507202149, discount_factors), 100.0)


def test_crra_certainty_equivalent_is_consistent_for_constant_samples() -> None:
    strategy = np.array([120.0, 120.0], dtype=float)
    benchmark = np.array([100.0, 100.0], dtype=float)

    assert np.isclose(certainty_equivalent(strategy, gamma=2.0), 120.0)
    assert np.isclose(relative_certainty_equivalent(strategy, benchmark, gamma=2.0), 0.2)


def test_trailing_moving_average_and_regime_mapping() -> None:
    rates = np.array([0.01, 0.02, 0.03, 0.04], dtype=float)

    assert np.isclose(trailing_moving_average(rates[:2], 5), 0.015)
    assert np.isclose(trailing_moving_average(rates, 2), 0.035)
    assert regime_from_rate_vs_ma(0.05, 0.04) == "hoge_reele_rente"
    assert regime_from_rate_vs_ma(0.03, 0.04) == "lage_reele_rente"
    assert regime_from_rate_vs_ma(0.04, 0.04) == "neutraal"


def test_rule_based_lifecycle_uses_moving_average_signal() -> None:
    table = _lifecycle_table()
    previous_returns = np.zeros(3, dtype=float)

    high = rule_based_lifecycle(previous_returns, 30, 0.05, 0.04, table)
    low = rule_based_lifecycle(previous_returns, 30, 0.03, 0.04, table)
    neutral = rule_based_lifecycle(previous_returns, 30, 0.04, 0.04, table)

    assert high == [0.7, 0.2, 0.1]
    assert low == [0.2, 0.3, 0.5]
    assert neutral == [0.5, 0.3, 0.2]


def test_three_regime_lifecycle_uses_moving_average_signal() -> None:
    table = _backtest_table()
    previous_returns = np.zeros(3, dtype=float)

    high = three_regime_lifecycle(previous_returns, 30, 0.05, 0.04, table)
    low = three_regime_lifecycle(previous_returns, 30, 0.03, 0.04, table)
    neutral = three_regime_lifecycle(previous_returns, 30, 0.04, 0.04, table)

    assert high == [0.7, 0.2, 0.1]
    assert low == [0.2, 0.3, 0.5]
    assert neutral == [0.5, 0.3, 0.2]
