"""Rule-based lifecycle policy loaded from a CSV table."""

from pathlib import Path

import numpy as np
import pandas as pd

from asset_optimizer.lifecycle.regime_signal import regime_from_rate_vs_ma


ASSET_COLUMNS = ["Euro_Staat", "Euro_ILBs", "Aandelen"]


def load_lifecycle_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights from a tidy CSV file."""

    table = pd.read_csv(path)
    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)
    return table


def rule_based_lifecycle(
    previous_returns: np.ndarray,
    age: int,
    current_interest_rate: float,
    interest_rate_ma: float,
    table: pd.DataFrame,
) -> list[float]:
    """Select a lifecycle state and return weights for the current age.

    The third and fourth arguments are the current rate and its moving average.
    """

    previous_returns = np.asarray(previous_returns, dtype=float)
    assert previous_returns.shape == (len(ASSET_COLUMNS),)

    lifecycle = regime_for_state(current_interest_rate, interest_rate_ma)

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    assert len(row) == 1

    return row.iloc[0][ASSET_COLUMNS].to_numpy(dtype=float).tolist()


def regime_for_state(current_interest_rate: float, interest_rate_ma: float) -> str:
    """Return the regime selected from the current rate and its moving average."""

    return regime_from_rate_vs_ma(current_interest_rate, interest_rate_ma)
