"""Load the historical US backtest data from FRED and S&P 500 prices."""

from dataclasses import dataclass
from pathlib import Path
import urllib.request

import numpy as np
import pandas as pd

from asset_optimizer.data.loader import ScenarioSet


FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
SP500_TICKER = "^GSPC"

FRED_SERIES = {
    "DGS10": "Long_Interest_Rate",
    "EXPINF1YR": "Expected_Inflation",
    "REAINTRATREARAT10Y": "Real_Interest_Rate",
    "CPIAUCSL": "CPI",
}

ASSET_COLUMNS = ["Bond_Return", "ILB_Return", "Equity_Return"]
STATE_COLUMNS = ["Expected_Inflation", "Expected_Inflation_Change", "Long_Interest_Rate"]
BACKTEST_DETAIL_COLUMNS = [
    "Inflation",
    "Real_Rate_ExPost",
    "Real_Rate_Cleveland",
    "ILB_Return_ExPost",
    "ILB_Return_Cleveland",
]
REQUIRED_COLUMNS = STATE_COLUMNS + ASSET_COLUMNS
OUTPUT_COLUMNS = STATE_COLUMNS + BACKTEST_DETAIL_COLUMNS + ASSET_COLUMNS
ILB_PROXY_COLUMNS = {
    "cleveland": "ILB_Return_Cleveland",
    "ex_post": "ILB_Return_ExPost",
    "expost": "ILB_Return_ExPost",
}


@dataclass(frozen=True)
class USBacktestData:
    """Annual observed backtest data."""

    annual: pd.DataFrame

    @property
    def asset_returns(self) -> pd.DataFrame:
        return self.annual[ASSET_COLUMNS]

    @property
    def state_variables(self) -> pd.DataFrame:
        return self.annual[STATE_COLUMNS]

    def to_scenario_set(self) -> ScenarioSet:
        """Represent the observed backtest as one deterministic scenario."""

        return ScenarioSet(
            asset_returns=self.asset_returns.to_numpy(dtype=float)[None, :, :],
            asset_names=list(ASSET_COLUMNS),
            horizon_years=len(self.asset_returns),
        )


def load_us_backtest_data(
    *,
    start_year: int = 1980,
    end_year: int | None = None,
    ilb_proxy: str = "cleveland",
    fred_monthly: pd.DataFrame | None = None,
    equity_returns: pd.Series | None = None,
    drop_missing: bool = True,
) -> USBacktestData:
    """Load annual US backtest assets and state variables."""

    if fred_monthly is None:
        fred_monthly = load_fred_monthly_data()

    if equity_returns is None:
        equity_returns = load_sp500_price_returns(start_year=start_year - 1, end_year=end_year)

    annual = build_annual_backtest_frame(fred_monthly, equity_returns, ilb_proxy=ilb_proxy)
    annual = annual[annual.index >= start_year]

    if end_year is not None:
        annual = annual[annual.index <= end_year]
    if drop_missing:
        annual = annual.dropna(subset=REQUIRED_COLUMNS)

    return USBacktestData(annual=annual)


def load_clean_us_backtest_data(
    path: str | Path,
    *,
    ilb_proxy: str | None = None,
    drop_missing: bool = True,
) -> USBacktestData:
    """Load a prepared annual backtest file with the required columns."""

    path = Path(path)
    if path.suffix.lower() == ".csv":
        annual = pd.read_csv(path)
    else:
        annual = pd.read_excel(path)

    assert {"Year", *REQUIRED_COLUMNS}.issubset(annual.columns)

    annual = annual.set_index("Year").sort_index()
    annual.index = annual.index.astype(int)

    for column in annual.columns:
        annual[column] = pd.to_numeric(annual[column], errors="coerce")

    if ilb_proxy is not None:
        annual = _select_ilb_proxy(annual, ilb_proxy)

    if drop_missing:
        annual = annual.dropna(subset=REQUIRED_COLUMNS)

    return USBacktestData(annual=annual)


def write_clean_us_backtest_data(data: USBacktestData, path: str | Path) -> None:
    """Write annual backtest inputs to CSV or Excel for reproducible notebook use."""

    path = Path(path)
    annual = data.annual.copy()
    annual.index.name = "Year"
    annual = annual.reset_index()

    if path.suffix.lower() == ".csv":
        annual.to_csv(path, index=False)
    else:
        annual.to_excel(path, index=False)


def load_fred_monthly_data() -> pd.DataFrame:
    """Download monthly FRED data needed for states and bond proxies."""

    series = {
        output_name: load_fred_series(series_id)
        for series_id, output_name in FRED_SERIES.items()
    }
    monthly = pd.concat(series.values(), axis=1).sort_index()
    monthly.columns = list(series)
    monthly = monthly.resample("ME").last()

    return monthly


def load_fred_series(series_id: str) -> pd.Series:
    """Download one FRED CSV series."""

    request = urllib.request.Request(
        FRED_CSV_URL.format(series_id=series_id) + "&cosd=1970-01-01",
        headers={"User-Agent": "curl/8.5.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        df = pd.read_csv(response)
    assert {"observation_date", series_id}.issubset(df.columns)

    values = pd.to_numeric(df[series_id].replace(".", np.nan), errors="coerce")
    values.index = pd.to_datetime(df["observation_date"])
    values = values.dropna().sort_index()
    values.name = series_id

    return values


def load_sp500_price_returns(
    *,
    ticker: str = SP500_TICKER,
    start_year: int = 1979,
    end_year: int | None = None,
) -> pd.Series:
    """Download annual S&P 500 price returns from Yahoo Finance."""

    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("Install yfinance to download S&P 500 price returns.") from exc

    start = f"{start_year}-01-01"
    end = None if end_year is None else f"{end_year + 1}-01-01"
    prices = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)

    if prices.empty:
        raise ValueError(f"No S&P 500 prices downloaded for {ticker!r}.")

    close = prices["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]

    annual_prices = close.dropna().resample("YE").last()
    returns = annual_prices.pct_change()
    returns.index = returns.index.year
    returns.name = "Equity_Return"

    return returns


def build_annual_backtest_frame(
    fred_monthly: pd.DataFrame,
    equity_returns: pd.Series,
    *,
    ilb_proxy: str = "cleveland",
) -> pd.DataFrame:
    """Create annual assets and annual state variables."""

    monthly = fred_monthly.copy()
    assert {"Long_Interest_Rate", "Expected_Inflation", "Real_Interest_Rate", "CPI"}.issubset(
        monthly.columns
    )

    monthly["Long_Interest_Rate"] = _percent_to_decimal(monthly["Long_Interest_Rate"])
    monthly["Expected_Inflation"] = _percent_to_decimal(monthly["Expected_Inflation"])
    monthly["Real_Interest_Rate"] = _percent_to_decimal(monthly["Real_Interest_Rate"])
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
    annual = _select_ilb_proxy(annual, ilb_proxy)
    annual.index.name = "Year"

    return annual[OUTPUT_COLUMNS]


def _percent_to_decimal(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").astype(float)
    median_abs = values.abs().median()
    if pd.notna(median_abs) and median_abs > 1.0:
        values = values / 100.0
    return values


def _select_ilb_proxy(annual: pd.DataFrame, ilb_proxy: str) -> pd.DataFrame:
    proxy_key = ilb_proxy.lower()
    if proxy_key not in ILB_PROXY_COLUMNS:
        raise ValueError(f"Unknown ILB proxy: {ilb_proxy!r}. Use 'cleveland' or 'ex_post'.")

    proxy_column = ILB_PROXY_COLUMNS[proxy_key]
    if proxy_column not in annual.columns:
        raise ValueError(f"Clean backtest file is missing {proxy_column!r}.")

    annual = annual.copy()
    annual["ILB_Return"] = annual[proxy_column]
    return annual
