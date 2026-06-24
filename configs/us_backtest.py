"""Scenario loading config for the US historical backtest workbook."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

BACKTEST_CONFIG = {
    "horizon_years": 43,
    "rf": 0.0,
    "assets": {
        "file": DATA_DIR / "us_backtest_scenarios.xlsx",
        "settings": {
            "header": None,
        },
        "sheets": {
            "Bond_Return": "Bond_Return",
            "ILB_Return": "ILB_Return",
            "Equity_Return": "Equity_Return",
            "Inflation": "Inflation",
            "Long_Interest_Rate": "Long_Interest_Rate",
            "Expected_Inflation": "Expected_Inflation",
        },
    },
    "yield": {
        "file": None,
    },
    "bei": {
        "file": None,
    },
}
