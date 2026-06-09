"""Rule-based lifecycle policy loaded from a CSV table."""

from pathlib import Path

import numpy as np
import pandas as pd


ASSET_COLUMNS = ["Euro_Staat", "Euro_ILBs", "Aandelen"]
LOW_REAL_RATE = 0.01
HIGH_REAL_RATE = 0.03
HIGH_INFLATION = 0.04


def load_lifecycle_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights from a tidy CSV file."""

    table = pd.read_csv(path)
    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)
    return table


def rule_based_lifecycle(
    previous_returns: np.ndarray,
    age: int,
    previous_interest_rate: float,
    previous_inflation: float,
    table: pd.DataFrame,
) -> list[float]:
    """Select a lifecycle state and return weights for the current age."""

    previous_returns = np.asarray(previous_returns, dtype=float)
    assert previous_returns.shape == (len(ASSET_COLUMNS),)

    lifecycle = regime_for_state(previous_interest_rate, previous_inflation)

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    assert len(row) == 1

    return row.iloc[0][ASSET_COLUMNS].to_numpy(dtype=float).tolist()


def regime_for_state(previous_interest_rate: float, previous_inflation: float) -> str:
    """Return the regime selected from 10y rate and inflation."""

    real_rate = previous_interest_rate

    if previous_inflation > HIGH_INFLATION and real_rate < LOW_REAL_RATE:
        return "hoge_inflatie_lage_reele_rente"
    if real_rate > HIGH_REAL_RATE:
        return "hoge_reele_rente"
    if real_rate < LOW_REAL_RATE:
        return "lage_reele_rente"
    return "neutraal"
