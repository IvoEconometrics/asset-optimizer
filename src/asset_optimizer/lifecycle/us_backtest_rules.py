"""Three-regime lifecycle rules for the US historical backtest."""

from pathlib import Path

import numpy as np
import pandas as pd


ASSET_COLUMNS = ["Bond_Return", "ILB_Return", "Equity_Return"]
LIFECYCLE_COLUMN_MAP = {
    "Euro_Staat": "Bond_Return",
    "Euro_ILBs": "ILB_Return",
    "Aandelen": "Equity_Return",
}
REGIMES = ["neutraal", "hoge_reele_rente", "lage_reele_rente"]

LOW_RATE = 0.01
HIGH_RATE = 0.03
STRONG_EXPECTED_INFLATION_INCREASE = 0.01


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
    long_interest_rate: float,
    expected_inflation_change: float,
    table: pd.DataFrame,
    strong_expected_inflation_increase: float = STRONG_EXPECTED_INFLATION_INCREASE,
) -> list[float]:
    """Select one of three lifecycle tables from rate and inflation expectations."""

    previous_returns = np.asarray(previous_returns, dtype=float)
    assert previous_returns.shape == (len(ASSET_COLUMNS),)

    if long_interest_rate >= HIGH_RATE:
        lifecycle = "hoge_reele_rente"
    elif long_interest_rate < LOW_RATE and expected_inflation_change < strong_expected_inflation_increase:
        lifecycle = "lage_reele_rente"
    else:
        lifecycle = "neutraal"

    age = min(max(age, int(table["age"].min())), int(table["age"].max()))
    row = table[(table["lifecycle"] == lifecycle) & (table["age"] == age)]
    assert len(row) == 1

    return row.iloc[0][ASSET_COLUMNS].to_numpy(dtype=float).tolist()
