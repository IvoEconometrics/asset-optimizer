"""Build the US backtest scenario workbook from local Excel exports."""

from pathlib import Path
import shutil

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "us_backtest"
OUTPUT_PATH = PROJECT_ROOT / "data" / "us_backtest_scenarios.xlsx"
DOWNLOADS_DIR = Path.home() / "Downloads"

START_YEAR = 1980
END_YEAR = pd.Timestamp.today().year - 1
ILB_PROXY = "cleveland"

LOCAL_EXCEL_FILES = {
    "CPIAUCSL.xlsx": ["CPIAUCSL.xlsx"],
    "DGS10.xlsx": ["DGS10 (1).xlsx", "DGS10.xlsx"],
    "EXPINF1YR.xlsx": ["EXPINF1YR.xlsx"],
    "NASDAQCOM.xlsx": ["NASDAQCOM.xlsx"],
    "REAINTRATREARAT10Y.xlsx": ["REAINTRATREARAT10Y.xlsx"],
}
FRED_SERIES = {
    "DGS10": "Long_Interest_Rate",
    "EXPINF1YR": "Expected_Inflation",
    "REAINTRATREARAT10Y": "Real_Interest_Rate",
    "CPIAUCSL": "CPI",
}
ILB_PROXY_COLUMNS = {
    "cleveland": "ILB_Return_Cleveland",
    "ex_post": "ILB_Return_ExPost",
    "expost": "ILB_Return_ExPost",
}
OUTPUT_SHEETS = [
    "Bond_Return",
    "ILB_Return",
    "Equity_Return",
    "Inflation",
    "Long_Interest_Rate",
    "Expected_Inflation",
]


# Copy manually downloaded sources when they are present, while still allowing
# the checked raw-data folder to be the source of truth.
RAW_DIR.mkdir(parents=True, exist_ok=True)
missing = []
for target_name, source_names in LOCAL_EXCEL_FILES.items():
    target = RAW_DIR / target_name
    source = next((DOWNLOADS_DIR / name for name in source_names if (DOWNLOADS_DIR / name).exists()), None)
    if source is not None:
        shutil.copy2(source, target)
    elif not target.exists():
        missing.append(" or ".join(str(DOWNLOADS_DIR / name) for name in source_names))

if missing:
    raise FileNotFoundError("Missing local Excel source files:\n" + "\n".join(missing))


# Read the raw FRED-style Excel exports.
series = {}
for series_id, output_name in FRED_SERIES.items():
    path = RAW_DIR / f"{series_id}.xlsx"
    workbook = pd.ExcelFile(path)
    data_sheet = workbook.sheet_names[1]
    df = pd.read_excel(path, sheet_name=data_sheet)
    assert {"observation_date", series_id}.issubset(df.columns)

    values = pd.to_numeric(df[series_id], errors="coerce")
    values.index = pd.to_datetime(df["observation_date"])
    series[output_name] = values.dropna().sort_index()

monthly = pd.concat(series.values(), axis=1).sort_index()
monthly.columns = list(series)
monthly = monthly.resample("ME").last()

equity_path = RAW_DIR / "NASDAQCOM.xlsx"
equity_workbook = pd.ExcelFile(equity_path)
equity_sheet = equity_workbook.sheet_names[1]
equity_df = pd.read_excel(equity_path, sheet_name=equity_sheet)
assert {"observation_date", "NASDAQCOM"}.issubset(equity_df.columns)

equity_prices = pd.to_numeric(equity_df["NASDAQCOM"], errors="coerce")
equity_prices.index = pd.to_datetime(equity_df["observation_date"])
equity_prices = equity_prices.dropna().sort_index()
annual_prices = equity_prices.resample("YE").last()
equity_returns = annual_prices.pct_change()
equity_returns.index = equity_returns.index.year
equity_returns.name = "Equity_Return"


# Build annual state and return series.
for column in ["Long_Interest_Rate", "Expected_Inflation", "Real_Interest_Rate"]:
    values = pd.to_numeric(monthly[column], errors="coerce").astype(float)
    median_abs = values.abs().median()
    if pd.notna(median_abs) and median_abs > 1.0:
        values = values / 100.0
    monthly[column] = values

monthly["Inflation"] = monthly["CPI"].pct_change(12, fill_method=None)
monthly["Real_Rate_ExPost"] = monthly["Long_Interest_Rate"] - monthly["Inflation"]
monthly["Real_Rate_Cleveland"] = monthly["Real_Interest_Rate"]

annual_source = monthly.groupby(monthly.index.year).last()
annual = pd.DataFrame(index=annual_source.index.astype(int))
annual["Expected_Inflation"] = annual_source["Expected_Inflation"]
annual["Long_Interest_Rate"] = annual_source["Long_Interest_Rate"]
annual["Inflation"] = annual_source["Inflation"]
annual["Expected_Inflation_Change"] = annual["Expected_Inflation"] - annual["Inflation"]
annual["Real_Rate_ExPost"] = annual_source["Real_Rate_ExPost"]
annual["Real_Rate_Cleveland"] = annual_source["Real_Rate_Cleveland"]
annual["Bond_Return"] = -10.0 * annual["Long_Interest_Rate"].diff()
annual["ILB_Return_ExPost"] = (
    annual["Inflation"]
    + annual["Real_Rate_ExPost"].shift(1)
    - 10.0 * annual["Real_Rate_ExPost"].diff()
)
annual["ILB_Return_Cleveland"] = (
    annual["Inflation"]
    + annual["Real_Rate_Cleveland"].shift(1)
    - 10.0 * annual["Real_Rate_Cleveland"].diff()
)
annual["Equity_Return"] = equity_returns

proxy_key = ILB_PROXY.lower()
if proxy_key not in ILB_PROXY_COLUMNS:
    raise ValueError(f"Unknown ILB proxy: {ILB_PROXY!r}.")
annual["ILB_Return"] = annual[ILB_PROXY_COLUMNS[proxy_key]]

annual = annual[(annual.index >= START_YEAR) & (annual.index <= END_YEAR)]
annual = annual.dropna(subset=OUTPUT_SHEETS)
annual.index.name = "Year"


# Write one sheet per series in the shape that load_assets already reads:
# one scenario row and years across columns.
with pd.ExcelWriter(OUTPUT_PATH) as writer:
    pd.DataFrame([annual.index.to_numpy()]).to_excel(
        writer,
        sheet_name="Year",
        index=False,
        header=False,
    )
    for column in OUTPUT_SHEETS:
        pd.DataFrame([annual[column].to_numpy(dtype=float)]).to_excel(
            writer,
            sheet_name=column,
            index=False,
            header=False,
        )

print(f"Wrote backtest scenario workbook to: {OUTPUT_PATH}")
print(f"Rows: {len(annual)}")
print(f"Years: {annual.index.min()}-{annual.index.max()}")
print(annual[OUTPUT_SHEETS].tail().to_string())
