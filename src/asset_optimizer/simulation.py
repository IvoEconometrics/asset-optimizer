"""Generic lifecycle simulation mechanics."""

from collections.abc import Callable

import numpy as np

from asset_optimizer.loader import ScenarioSet


def run_lifecycle_simulation(
    scenario_set: ScenarioSet,
    *,
    current_age: int,
    retirement_age: int = 68,
    start_capital: float = 100.0,
    annual_contribution: float = 0.0,
    lifecycle_assets: tuple[str, ...],
    benchmark_name: str | None = None,
    policy: Callable[[ScenarioSet, int, int, int, np.ndarray], list[float] | np.ndarray],
) -> dict[str, np.ndarray | int]:
    """Run annual rebalanced lifecycle paths with a caller-supplied policy."""

    years_to_retirement = retirement_age - current_age
    if years_to_retirement < 1:
        raise ValueError("current_age must be below retirement_age.")
    if start_capital <= 0:
        raise ValueError("start_capital must be positive.")

    years = min(years_to_retirement, scenario_set.horizon_years)
    asset_indices = [scenario_set.asset_names.index(name) for name in lifecycle_assets]
    lifecycle_returns = scenario_set.asset_returns[:, :years, asset_indices]

    if benchmark_name is None:
        benchmark_returns = np.zeros((scenario_set.m, years), dtype=float)
    else:
        benchmark_index = scenario_set.asset_names.index(benchmark_name)
        benchmark_returns = scenario_set.asset_returns[:, :years, benchmark_index]

    capital = np.full(scenario_set.m, float(start_capital), dtype=float)
    benchmark_level = np.ones(scenario_set.m, dtype=float)
    capital_paths = np.empty((scenario_set.m, years + 1), dtype=float)
    real_capital_paths = np.empty((scenario_set.m, years + 1), dtype=float)
    weights = np.empty((scenario_set.m, years, len(lifecycle_assets)), dtype=float)

    capital_paths[:, 0] = capital
    real_capital_paths[:, 0] = capital

    for year_index in range(years):
        age = current_age + year_index

        for scenario_index in range(scenario_set.m):
            if year_index == 0:
                previous_returns = np.zeros(len(lifecycle_assets), dtype=float)
            else:
                previous_returns = lifecycle_returns[scenario_index, year_index - 1, :]

            year_weights = np.asarray(
                policy(
                    scenario_set,
                    scenario_index,
                    year_index,
                    age,
                    previous_returns,
                ),
                dtype=float,
            )
            if year_weights.shape != (len(lifecycle_assets),):
                raise ValueError(
                    f"policy returned weights with shape {year_weights.shape}, "
                    f"expected {(len(lifecycle_assets),)}."
                )

            weights[scenario_index, year_index] = year_weights
            portfolio_return = float(lifecycle_returns[scenario_index, year_index] @ year_weights)
            capital[scenario_index] = (capital[scenario_index] + annual_contribution) * (
                1.0 + portfolio_return
            )

        benchmark_level *= 1.0 + benchmark_returns[:, year_index]
        capital_paths[:, year_index + 1] = capital
        real_capital_paths[:, year_index + 1] = capital / benchmark_level

    return {
        "years": years,
        "capital_paths": capital_paths,
        "real_capital_paths": real_capital_paths,
        "final_capital": capital_paths[:, -1],
        "final_real_capital": real_capital_paths[:, -1],
        "weights": weights,
    }
