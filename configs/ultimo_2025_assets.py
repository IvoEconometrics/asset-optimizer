"""Assets-only scenario loading config for the Ultimo 2025 asset universe."""

from configs.ultimo_2025 import ASSET_FILE, ASSET_SETTINGS, ASSET_SHEETS


SCENARIO_CONFIG = {
    "horizon_years": 15,
    "rf": 0.02,
    "assets": {
        "file": ASSET_FILE,
        "settings": ASSET_SETTINGS,
        "sheets": ASSET_SHEETS,
    },
    "yield": None,
    "bei": None,
}
