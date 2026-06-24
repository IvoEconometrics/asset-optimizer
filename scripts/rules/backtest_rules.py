"""Backtest-specific lifecycle rules."""

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.rules.lifecycle_table_rules import regime_from_rate_vs_ma, trailing_moving_average


ASSET_COLUMNS = ["Bond_Return", "ILB_Return", "Equity_Return"]
LIFECYCLE_COLUMN_MAP = {
    "Euro_Staat": "Bond_Return",
    "Euro_ILBs": "ILB_Return",
    "Aandelen": "Equity_Return",
}


def load_backtest_lifecycle_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights and map them to the backtest asset names."""

    table = pd.read_csv(path)
    if not set(ASSET_COLUMNS).issubset(table.columns):
        table = table.rename(columns=LIFECYCLE_COLUMN_MAP)

    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)
    return table


def backtest_lifecycle_rule(
    scenario_set,
    scenario_index: int,
    year_index: int,
    age: int,
    previous_returns: np.ndarray,
    *,
    table: pd.DataFrame,
    lifecycle_assets: tuple[str, ...],
    signal_name: str = "Long_Interest_Rate",
    ma_window_years: int = 5,
) -> list[float]:
    """Select a backtest lifecycle row from a signal in the scenario set."""

    previous_returns = np.asarray(previous_returns, dtype=float)
    if previous_returns.shape != (len(lifecycle_assets),):
        raise ValueError(
            f"previous_returns must have shape {(len(lifecycle_assets),)}, got {previous_returns.shape}."
        )

    signal_index = scenario_set.asset_names.index(signal_name)
    signal_history = scenario_set.asset_returns[scenario_index, : year_index + 1, signal_index]
    current_rate = float(signal_history[-1])
    moving_average = trailing_moving_average(signal_history, ma_window_years)
    lifecycle = regime_from_rate_vs_ma(current_rate, moving_average)

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    if len(row) != 1:
        raise ValueError(f"Expected one lifecycle row for {lifecycle!r} age {age}, got {len(row)}.")

    return row.iloc[0][list(lifecycle_assets)].to_numpy(dtype=float).tolist()
