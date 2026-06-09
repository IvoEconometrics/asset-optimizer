"""Scenario loading config for the Ultimo 2025 asset universe."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

SCENARIO_CONFIG = {
    "horizon_years": 15,
    "rf": 0.02,
    "assets": {
        "file": DATA_DIR / "Flags & Frictions - Ultimo 2025 - Overzicht Rendementen & Inflatie.xlsx",
        "settings": {
            "skiprows": 18,
            "nrows": 2000,
            "usecols": "C:Q",
            "header": None,
        },
        "sheets": {
            "Bank_Loans": "6. Rendement Bank Loans",
            "Commodities": "18. Rendement Grondstoffen",
            "EMD_HC": "10. Rendement EMD HC",
            "Emerging_Equity": "3. Rendement Aandelen Opkomende",
            "Aandelen": "4. Rendement Aandelen Wereld DC",
            "Euro_ILBs": "13. Rendement Euro ILBs",
            "Euro_Staat": "14. Rendement Euro Staatsobliga",
            "Global_HY": "15. Rendement Global High Yield",
            "Global_IG_Credits": "16. Rendement Global IG Credits",
            "Hedge_Funds": "19. Rendement Hedge Funds",
            "Inflatie": "2. Prijsinflatie NL",
            "NL_Mortgages": "22. Rendement Nederlandse Hypot",
            "Private_Equity": "25. Rendement Private Equity",
            "Private_Infrastructure": "23. Rendement Privaat Infrastru",
            "Private_Real_Estate": "24. Rendement Privaat Vastgoed ",
        },
    },
    "yield": {
        "file": DATA_DIR / "Flags & Frictions - Ultimo 2025 - Swaprente.xlsx",
        "projection_years": 60,
        "tenor_years": 120,
        "sheet_template": "NOM {year}",
        "settings": {
            "skiprows": 3,
            "nrows": 2000,
            "usecols": "C:DR",
            "header": None,
        },
    },
}

LIFECYCLE_ASSETS = ("Euro_Staat", "Euro_ILBs", "Aandelen")
