"""Smoke tests for lifecycle simulation paths."""

import numpy as np
import pandas as pd

from asset_optimizer.data.loader import ScenarioSet
from asset_optimizer.lifecycle.simulation import run_lifecycle_simulation
from asset_optimizer.lifecycle.stochastic_regime import run_stochastic_regime_lifecycle


def _make_scenario_set() -> ScenarioSet:
    asset_returns = np.array(
        [
            [
                [0.01, 0.00, 0.02, 0.02],
                [0.02, 0.00, 0.02, 0.02],
                [0.03, 0.00, 0.02, 0.02],
            ]
        ],
        dtype=float,
    )
    yields = np.array([[[0.01], [0.03], [0.05]]], dtype=float)
    bei = np.array([[[0.00], [0.01], [0.01]]], dtype=float)

    return ScenarioSet(
        asset_returns=asset_returns,
        asset_names=["Euro_Staat", "Euro_ILBs", "Aandelen", "Inflatie"],
        horizon_years=3,
        yields=yields,
        yield_tenors=[10],
        bei=bei,
        bei_tenors=[10],
    )


def _three_regime_table() -> pd.DataFrame:
    rows = []
    for lifecycle in ["neutraal", "hoge_reele_rente", "lage_reele_rente"]:
        for age in [25, 26, 27]:
            rows.append(
                {
                    "lifecycle": lifecycle,
                    "age": age,
                    "Euro_Staat": 1.0,
                    "Euro_ILBs": 0.0,
                    "Aandelen": 0.0,
                }
            )
    return pd.DataFrame(rows)


def test_run_lifecycle_simulation_passes_rate_moving_average_to_policy() -> None:
    scenario_set = _make_scenario_set()
    calls = []

    def policy(previous_returns, age, current_interest_rate, interest_rate_ma):
        calls.append((age, current_interest_rate, interest_rate_ma))
        return [1.0, 0.0, 0.0]

    final_real_capital = run_lifecycle_simulation(
        scenario_set,
        current_age=25,
        retirement_age=28,
        start_capital=100.0,
        annual_contribution=0.0,
        lifecycle_assets=("Euro_Staat", "Euro_ILBs", "Aandelen"),
        benchmark_name="Inflatie",
        policy=policy,
        inflation_name="Inflatie",
        rate_tenor=10,
        ma_window_years=2,
    )

    assert final_real_capital.shape == (1,)
    assert np.isfinite(final_real_capital).all()
    assert len(calls) == 4
    assert np.allclose([call[2] for call in calls[1:]], [0.01, 0.02, 0.04])


def test_stochastic_regime_lifecycle_uses_moving_average_regimes() -> None:
    scenario_set = _make_scenario_set()
    table = _three_regime_table()

    result = run_stochastic_regime_lifecycle(
        scenario_set,
        table,
        current_age=25,
        retirement_age=28,
        start_capital=100.0,
        annual_contribution=0.0,
        use_regimes=True,
        inflation_index_contribution=False,
        ma_window_years=2,
    )

    assert result["years"] == 3
    assert np.isfinite(result["final_real_capital"]).all()
    assert result["regime_counts"] == {
        "neutraal": 1,
        "hoge_reele_rente": 2,
        "lage_reele_rente": 0,
    }
