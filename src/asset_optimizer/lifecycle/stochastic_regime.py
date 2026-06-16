"""Lifecycle simulation with stochastic NOM/BEI regime states."""

from pathlib import Path

import numpy as np
import pandas as pd

from asset_optimizer.data.loader import ScenarioSet
from asset_optimizer.lifecycle.regime_signal import regime_from_rate_vs_ma, trailing_moving_average


ASSET_COLUMNS = ["Euro_Staat", "Euro_ILBs", "Aandelen"]
REGIMES = ["neutraal", "hoge_reele_rente", "lage_reele_rente"]


def load_three_regime_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights and keep the three regimes used here."""

    table = pd.read_csv(path)
    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)

    table = table[table["lifecycle"].isin(REGIMES)].copy()
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)

    return table


def run_stochastic_regime_lifecycle(
    scenario_set: ScenarioSet,
    table: pd.DataFrame,
    *,
    current_age: int = 25,
    retirement_age: int = 68,
    start_capital: float = 100.0,
    annual_contribution: float = 100.0,
    initial_inflation: float = 0.02,
    use_regimes: bool = True,
    inflation_index_contribution: bool = True,
    lifecycle_assets: tuple[str, ...] = tuple(ASSET_COLUMNS),
    inflation_name: str = "Inflatie",
    nominal_tenor: int = 10,
    expected_inflation_short_tenor: int = 1,
    expected_inflation_long_tenor: int = 10,
    ma_window_years: int = 5,
) -> dict:
    """Run a simple annual lifecycle using NOM/BEI states.

    State at year ``t`` comes from NOM/BEI sheet ``t``. The regime signal compares
    the current real-rate path against its trailing moving average. Real capital is
    measured against realised price inflation from the scenario set.
    """

    assert scenario_set.yields is not None
    assert scenario_set.yield_tenors is not None
    assert scenario_set.bei is not None
    assert scenario_set.bei_tenors is not None

    years_to_retirement = retirement_age - current_age
    if years_to_retirement < 1:
        raise ValueError("current_age must be below retirement_age.")

    years = min(years_to_retirement, scenario_set.horizon_years)

    asset_indices = [scenario_set.asset_names.index(name) for name in lifecycle_assets]
    inflation_index = scenario_set.asset_names.index(inflation_name)
    nominal_10y_index = scenario_set.yield_tenors.index(nominal_tenor)
    bei_10y_index = scenario_set.bei_tenors.index(expected_inflation_long_tenor)

    lifecycle_returns = scenario_set.asset_returns[:, :years, asset_indices]
    inflation_paths = scenario_set.asset_returns[:, :years, inflation_index]
    real_rate_paths = scenario_set.yields[:, :years, nominal_10y_index] - scenario_set.bei[:, :years, bei_10y_index]

    weights_by_age_regime = {}
    min_age = int(table["age"].min())
    max_age = int(table["age"].max())
    for _, row in table.iterrows():
        key = (str(row["lifecycle"]), int(row["age"]))
        weights_by_age_regime[key] = row[ASSET_COLUMNS].to_numpy(dtype=float)

    capital = np.full(scenario_set.m, float(start_capital), dtype=float)
    contribution = np.full(scenario_set.m, float(annual_contribution), dtype=float)
    price_index = np.ones(scenario_set.m, dtype=float)

    capital_paths = np.empty((scenario_set.m, years + 1), dtype=float)
    real_capital_paths = np.empty((scenario_set.m, years + 1), dtype=float)
    regimes = np.empty((scenario_set.m, years), dtype=object)

    capital_paths[:, 0] = capital
    real_capital_paths[:, 0] = capital

    for year_index in range(years):
        age = min(max(current_age + year_index, min_age), max_age)

        for scenario_index in range(scenario_set.m):
            if use_regimes:
                current_real_rate = real_rate_paths[scenario_index, year_index]
                rate_history = real_rate_paths[scenario_index, : year_index + 1]
                rate_ma = trailing_moving_average(rate_history, ma_window_years)
                regime = regime_from_rate_vs_ma(current_real_rate, rate_ma)
            else:
                regime = "neutraal"

            weights = weights_by_age_regime[(regime, age)]
            portfolio_return = float(lifecycle_returns[scenario_index, year_index] @ weights)
            capital[scenario_index] = (capital[scenario_index] + contribution[scenario_index]) * (
                1.0 + portfolio_return
            )
            regimes[scenario_index, year_index] = regime

        price_index *= 1.0 + inflation_paths[:, year_index]
        if inflation_index_contribution:
            contribution *= 1.0 + inflation_paths[:, year_index]

        capital_paths[:, year_index + 1] = capital
        real_capital_paths[:, year_index + 1] = capital / price_index

    regime_counts = {
        regime: int(np.sum(regimes == regime))
        for regime in REGIMES
    }

    return {
        "years": years,
        "capital_paths": capital_paths,
        "real_capital_paths": real_capital_paths,
        "final_real_capital": real_capital_paths[:, -1],
        "regimes": regimes,
        "regime_counts": regime_counts,
    }
