"""Build the clean annual US backtest input CSV from local FRED Excel exports."""

from pathlib import Path
import shutil

import pandas as pd

from asset_optimizer.data.us_backtest_loader import (
    USBacktestData,
    build_annual_backtest_frame,
    load_clean_us_backtest_data,
    write_clean_us_backtest_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "us_backtest"
OUTPUT_PATH = PROJECT_ROOT / "data" / "us_backtest_inputs.csv"
DOWNLOADS_DIR = Path.home() / "Downloads"
LOCAL_EXCEL_FILES = {
    "CPIAUCSL.xlsx": ["CPIAUCSL.xlsx"],
    "DGS10.xlsx": ["DGS10 (1).xlsx", "DGS10.xlsx"],
    "EXPINF1YR.xlsx": ["EXPINF1YR.xlsx"],
    "NASDAQCOM.xlsx": ["NASDAQCOM.xlsx"],
    "REAINTRATREARAT10Y.xlsx": ["REAINTRATREARAT10Y.xlsx"],
}


def copy_local_excel_sources(
    source_dir: Path = DOWNLOADS_DIR,
    raw_dir: Path = RAW_DIR,
) -> None:
    """Copy manually downloaded FRED Excel files into the raw data folder."""

    raw_dir.mkdir(parents=True, exist_ok=True)
    missing = []

    for target_name, source_names in LOCAL_EXCEL_FILES.items():
        source = next((source_dir / name for name in source_names if (source_dir / name).exists()), None)
        if source is None:
            missing.append(" or ".join(str(source_dir / name) for name in source_names))
            continue
        shutil.copy2(source, raw_dir / target_name)

    if missing:
        raise FileNotFoundError("Missing local Excel source files:\n" + "\n".join(missing))


def load_excel_raw(raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, pd.Series]:
    """Load manually downloaded FRED Excel files."""

    fred_series = {
        "DGS10": "Long_Interest_Rate",
        "EXPINF1YR": "Expected_Inflation",
        "REAINTRATREARAT10Y": "Real_Interest_Rate",
        "CPIAUCSL": "CPI",
    }

    series = {}
    for series_id, output_name in fred_series.items():
        values = read_fred_excel_series(raw_dir / f"{series_id}.xlsx", series_id)
        series[output_name] = values

    monthly = pd.concat(series.values(), axis=1).sort_index()
    monthly.columns = list(series)
    monthly = monthly.resample("ME").last()

    equity_prices = read_fred_excel_series(raw_dir / "NASDAQCOM.xlsx", "NASDAQCOM")
    annual_prices = equity_prices.resample("YE").last()
    equity_returns = annual_prices.pct_change()
    equity_returns.index = equity_returns.index.year
    equity_returns.name = "Equity_Return"

    return monthly, equity_returns


def read_fred_excel_series(path: Path, series_id: str) -> pd.Series:
    """Read one FRED Excel export and return its value series."""

    workbook = pd.ExcelFile(path)
    data_sheet = workbook.sheet_names[1]
    df = pd.read_excel(path, sheet_name=data_sheet)
    assert {"observation_date", series_id}.issubset(df.columns)

    values = pd.to_numeric(df[series_id], errors="coerce")
    values.index = pd.to_datetime(df["observation_date"])
    values = values.dropna().sort_index()
    values.name = series_id

    return values


def build_clean_csv(
    *,
    raw_dir: Path = RAW_DIR,
    output_path: Path = OUTPUT_PATH,
    start_year: int = 1980,
    end_year: int | None = None,
    ilb_proxy: str = "cleveland",
) -> USBacktestData:
    """Build the clean annual backtest CSV from raw downloaded files."""

    fred_monthly, equity_returns = load_excel_raw(raw_dir)

    annual = build_annual_backtest_frame(
        fred_monthly,
        equity_returns,
        ilb_proxy=ilb_proxy,
    )
    annual = annual[annual.index >= start_year]
    if end_year is None:
        end_year = pd.Timestamp.today().year - 1
    annual = annual[annual.index <= end_year]
    annual = annual.dropna()

    data = USBacktestData(annual=annual)
    write_clean_us_backtest_data(data, output_path)
    return data


def main() -> None:
    copy_local_excel_sources()
    data = build_clean_csv()
    checked = load_clean_us_backtest_data(OUTPUT_PATH)

    print(f"Wrote raw files to: {RAW_DIR}")
    print(f"Wrote clean file to: {OUTPUT_PATH}")
    print(f"Rows: {len(checked.annual)}")
    print(f"Years: {checked.annual.index.min()}-{checked.annual.index.max()}")
    print(checked.annual.tail().to_string())


if __name__ == "__main__":
    main()
