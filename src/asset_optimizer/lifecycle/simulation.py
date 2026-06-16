"""Simplified three-asset lifecycle simulation."""

from collections.abc import Callable

import numpy as np

from asset_optimizer.data.loader import ScenarioSet
from asset_optimizer.lifecycle.regime_signal import trailing_moving_average


def run_lifecycle_simulation(
    scenario_set: ScenarioSet,
    *,
    current_age: int,
    retirement_age: int = 68,
    start_capital: float = 100.0,
    annual_contribution: float = 0.0,
    lifecycle_assets: tuple[str, ...],
    benchmark_name: str,
    policy: Callable[[np.ndarray, int, float, float], list[float]],
    inflation_name: str = "Inflation",
    rate_tenor: int = 10,
    ma_window_years: int = 5,
):
    """
    Simulate annual rebalanced lifecycle paths in three assets.

    Real return is evaluated relative to the configured benchmark. That
    benchmark can be price inflation, wage inflation, or another asset series.
    The policy receives the current interest rate and its trailing moving average.
    """

    # Minimaal volle mep doorrekenen, anders korter kiezen.

    years_to_retirement = retirement_age - current_age

    if years_to_retirement < 1:
        raise ValueError("Current age misspecified. (Too low or too high)")
    if start_capital <= 0:
        raise ValueError("start_capital must be positive.")

    years = min(years_to_retirement, scenario_set.horizon_years)

    # Alle assets moeten in de set zitten.

    asset_indices = [scenario_set.asset_names.index(name) for name in lifecycle_assets]
    benchmark_asset_index = scenario_set.asset_names.index(benchmark_name)
    lifecycle_returns = scenario_set.asset_returns[:, :years, asset_indices]

    assert scenario_set.yields is not None
    assert scenario_set.yield_tenors is not None
    rate_tenor_index = scenario_set.yield_tenors.index(rate_tenor)

    assert len(lifecycle_assets) == lifecycle_returns.shape[2]

    m_scenarios = scenario_set.m
    n_assets = len(lifecycle_assets)

    # Policy Check
    test_previous_returns = np.zeros(n_assets, dtype=float)
    test_weights = np.asarray(policy(test_previous_returns, current_age, 0.02, 0.02), dtype=float)
    assert test_weights.shape == (n_assets,)

    # Initializeer matrices en paden

    capital = np.full(m_scenarios, float(start_capital))
    benchmark_index = np.ones(m_scenarios, dtype=float)

    capital_paths = np.empty((m_scenarios, years + 1), dtype=float)
    benchmark_paths = scenario_set.asset_returns[:, :years, benchmark_asset_index]
    real_capital_paths = np.empty((m_scenarios, years + 1), dtype=float)

    capital_paths[:, 0] = capital
    real_capital_paths[:, 0] = capital

    # Jaar loop

    for year_index in range(years):
        # Scenario loop

        for scenario_index in range(m_scenarios):
            if year_index == 0:
                previous_returns = np.zeros(n_assets, dtype=float)
            else:
                previous_returns = lifecycle_returns[scenario_index, year_index - 1, :]

            current_interest_rate = scenario_set.yields[scenario_index, year_index, rate_tenor_index]
            interest_rate_history = scenario_set.yields[scenario_index, : year_index + 1, rate_tenor_index]
            interest_rate_ma = trailing_moving_average(interest_rate_history, ma_window_years)

            age = current_age + year_index
            weights = np.asarray(
                policy(
                    previous_returns,
                    age,
                    float(current_interest_rate),
                    float(interest_rate_ma),
                ),
                dtype=float,
            )
            assert weights.shape == (n_assets,)

            portfolio_return = float(lifecycle_returns[scenario_index, year_index] @ weights)
            capital[scenario_index] = (capital[scenario_index] + annual_contribution) * (1.0 + portfolio_return)

        benchmark_index *= 1.0 + benchmark_paths[:, year_index]
        capital_paths[:, year_index + 1] = capital
        real_capital_paths[:, year_index + 1] = capital / benchmark_index

    final_real_capital = real_capital_paths[:, -1]

    return final_real_capital
