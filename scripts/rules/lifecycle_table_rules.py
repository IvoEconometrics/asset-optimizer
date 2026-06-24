"""Reusable lifecycle-table rules for simulations."""

from pathlib import Path

import numpy as np
import pandas as pd


ASSET_COLUMNS = ["Euro_Staat", "Euro_ILBs", "Aandelen"]
TABLE_COLUMN_MAP = {
    "Euro Staatsobligaties": "Euro_Staat",
    "Euro ILBs": "Euro_ILBs",
    "Aandelen Wereld DC": "Aandelen",
}
NEUTRAL_REGIME = "neutraal"
HIGH_RATE_REGIME = "hoge_reele_rente"
LOW_RATE_REGIME = "lage_reele_rente"


def load_lifecycle_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights from a tidy CSV file."""

    table = pd.read_csv(path)
    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)
    return table


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


def rule_based_lifecycle(
    scenario_set,
    scenario_index: int,
    year_index: int,
    age: int,
    previous_returns: np.ndarray,
    *,
    table: pd.DataFrame,
    lifecycle_assets: tuple[str, ...],
    signal_name: str,
    ma_window_years: int = 5,
) -> list[float]:
    """Select a lifecycle row using a signal extracted from the scenario set."""

    previous_returns = np.asarray(previous_returns, dtype=float)
    if previous_returns.shape != (len(lifecycle_assets),):
        raise ValueError(
            f"previous_returns must have shape {(len(lifecycle_assets),)}, got {previous_returns.shape}."
        )

    if signal_name.startswith("yield:"):
        if scenario_set.yields is None or scenario_set.yield_tenors is None:
            raise ValueError("signal_name uses a yield tenor, but scenario_set has no yields.")
        tenor = int(signal_name.split(":", 1)[1])
        signal_index = scenario_set.yield_tenors.index(tenor)
        signal_history = scenario_set.yields[scenario_index, : year_index + 1, signal_index]
    else:
        signal_index = scenario_set.asset_names.index(signal_name)
        signal_history = scenario_set.asset_returns[scenario_index, : year_index + 1, signal_index]

    current_rate = float(signal_history[-1])
    moving_average = trailing_moving_average(signal_history, ma_window_years)
    lifecycle = regime_from_rate_vs_ma(current_rate, moving_average)

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    if len(row) != 1:
        raise ValueError(f"Expected one lifecycle row for {lifecycle!r} age {age}, got {len(row)}.")

    table_columns = [TABLE_COLUMN_MAP.get(asset_name, asset_name) for asset_name in lifecycle_assets]
    return row.iloc[0][table_columns].to_numpy(dtype=float).tolist()
