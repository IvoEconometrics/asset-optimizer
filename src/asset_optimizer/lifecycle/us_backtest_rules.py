"""Three-regime lifecycle rules for the US historical backtest."""

from pathlib import Path

import numpy as np
import pandas as pd

from asset_optimizer.lifecycle.regime_signal import regime_from_rate_vs_ma


ASSET_COLUMNS = ["Bond_Return", "ILB_Return", "Equity_Return"]
LIFECYCLE_COLUMN_MAP = {
    "Euro_Staat": "Bond_Return",
    "Euro_ILBs": "ILB_Return",
    "Aandelen": "Equity_Return",
}
REGIMES = ["neutraal", "hoge_reele_rente", "lage_reele_rente"]


def load_three_regime_table(path: str | Path) -> pd.DataFrame:
    """Load lifecycle weights and keep only the three backtest regimes."""

    table = pd.read_csv(path)
    if not set(ASSET_COLUMNS).issubset(table.columns):
        table = table.rename(columns=LIFECYCLE_COLUMN_MAP)

    assert {"lifecycle", "age", *ASSET_COLUMNS}.issubset(table.columns)

    table = table[table["lifecycle"].isin(REGIMES)].copy()
    table[ASSET_COLUMNS] = table[ASSET_COLUMNS].div(table[ASSET_COLUMNS].sum(axis=1), axis=0)
    return table


def three_regime_lifecycle(
    previous_returns: np.ndarray,
    age: int,
    current_interest_rate: float,
    interest_rate_ma: float,
    table: pd.DataFrame,
) -> list[float]:
    """Select one of three lifecycle tables from the current rate and its moving average."""

    previous_returns = np.asarray(previous_returns, dtype=float)
    assert previous_returns.shape == (len(ASSET_COLUMNS),)

    lifecycle = regime_from_rate_vs_ma(current_interest_rate, interest_rate_ma)

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    assert len(row) == 1

    return row.iloc[0][ASSET_COLUMNS].to_numpy(dtype=float).tolist()
