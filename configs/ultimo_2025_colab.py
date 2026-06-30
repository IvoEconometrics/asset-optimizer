"""Compact 30-year Ultimo 2025 config for GitHub and Colab."""

from pathlib import Path

from configs.ultimo_2025 import ASSET_SHEETS as BASE_ASSET_SHEETS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "colab"

ASSET_FILE = DATA_DIR / "ultimo_2025_assets_30y.xlsx"
SWAP_FILE = DATA_DIR / "ultimo_2025_swap_30y.xlsx"
BEI_FILE = DATA_DIR / "ultimo_2025_bei_30y.xlsx"

ASSET_SETTINGS = {
    "skiprows": 18,
    "nrows": 2000,
    "usecols": "C:AF",
    "header": None,
}

CURVE_SETTINGS = {
    "skiprows": 3,
    "nrows": 2000,
    "usecols": "C:AF",
    "header": None,
}

ASSET_SHEETS = {}
for asset_name, sheet_name in BASE_ASSET_SHEETS.items():
    ASSET_SHEETS[asset_name] = sheet_name
    if asset_name == "Cash":
        ASSET_SHEETS["Direct Lending Europa"] = "8. Rendement Direct Lending Eur"

SCENARIO_CONFIG = {
    "horizon_years": 30,
    "rf": 0.02,
    "assets": {
        "file": ASSET_FILE,
        "settings": ASSET_SETTINGS,
        "sheets": ASSET_SHEETS,
    },
    "yield": {
        "file": SWAP_FILE,
        "projection_years": 30,
        "tenor_years": 30,
        "sheet_template": "NOM {year}",
        "first_sheet_year": 0,
        "settings": CURVE_SETTINGS,
    },
    "bei": {
        "file": BEI_FILE,
        "projection_years": 30,
        "tenor_years": 30,
        "sheet_template": "BEI {year}",
        "first_sheet_year": 0,
        "settings": CURVE_SETTINGS,
    },
}
