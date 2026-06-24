"""Scenario loading config for the Ultimo 2025 asset universe."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

ASSET_FILE = DATA_DIR / "Flags & Frictions - Ultimo 2025 - Overzicht Rendementen & Inflatie.xlsx"
SWAP_FILE = DATA_DIR / "Flags & Frictions - Ultimo 2025 - Swaprente.xlsx"
BEI_FILE = DATA_DIR / "Flags & Frictions - Ultimo 2025 - BEI.xlsx"

ASSET_SETTINGS = {
    "skiprows": 18,
    "nrows": 2000,
    "usecols": "C:Q",
    "header": None,
}

ASSET_SHEETS = {
    "Looninflatie NL": "1. Looninflatie NL",
    "Prijsinflatie NL": "2. Prijsinflatie NL",
    "Aandelen Opkomende Markten": "3. Rendement Aandelen Opkomende",
    "Aandelen Wereld DC": "4. Rendement Aandelen Wereld DC",
    "Aandelen Wereld DC Unhedged": "5. Rendement Aandelen Wereld DC",
    "Bank Loans": "6. Rendement Bank Loans",
    "Beursgenoteerd Vastgoed": "7. Rendement Beursgenoteerd Vas",
    "Cash": "8. Rendement Cash",
    "Duitse Staatsobligaties": "9. Rendement Duitse Staatsoblig",
    "EMD HC": "10. Rendement EMD HC",
    "EMD LC": "11. Rendement EMD LC",
    "Euro IG Credits": "12. Rendement Euro IG Credits",
    "Euro ILBs": "13. Rendement Euro ILBs",
    "Euro Staatsobligaties": "14. Rendement Euro Staatsobliga",
    "Global High Yield": "15. Rendement Global High Yield",
    "Global IG Credits": "16. Rendement Global IG Credits",
    "Global ILBs": "17. Rendement Global ILBs",
    "Grondstoffen": "18. Rendement Grondstoffen",
    "Hedge Funds": "19. Rendement Hedge Funds",
    "Internationaal Privaat Vastgoed": "20. Rendement Internationaal Pr",
    "Italisaanse Staatsobligaties": "21. Rendement Italisaanse Staat",
    "Nederlandse Hypotheken": "22. Rendement Nederlandse Hypot",
    "Privaat Infrastructuur": "23. Rendement Privaat Infrastru",
    "Privaat Vastgoed NL": "24. Rendement Privaat Vastgoed ",
    "Private Equity": "25. Rendement Private Equity",
}

CURVE_SETTINGS = {
    "skiprows": 3,
    "nrows": 2000,
    "usecols": "C:DR",
    "header": None,
}

SCENARIO_CONFIG = {
    "horizon_years": 15,
    "rf": 0.02,
    "assets": {
        "file": ASSET_FILE,
        "settings": ASSET_SETTINGS,
        "sheets": ASSET_SHEETS,
    },
    "yield": {
        "file": SWAP_FILE,
        "projection_years": 60,
        "tenor_years": 120,
        "sheet_template": "NOM {year}",
        "first_sheet_year": 0,
        "settings": CURVE_SETTINGS,
    },
    "bei": {
        "file": BEI_FILE,
        "projection_years": 60,
        "tenor_years": 120,
        "sheet_template": "BEI {year}",
        "first_sheet_year": 0,
        "settings": CURVE_SETTINGS,
    },
}
