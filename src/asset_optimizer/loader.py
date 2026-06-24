"""Load scenario matrices from workbook configs."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioSet:
    """Scenario data in matrix form."""

    asset_returns: np.ndarray
    asset_names: list[str]
    horizon_years: int
    yields: np.ndarray | None = None
    yield_tenors: list[int] | None = None
    bei: np.ndarray | None = None
    bei_tenors: list[int] | None = None

    @property
    def m(self) -> int:
        return int(self.asset_returns.shape[0])

    @property
    def n(self) -> int:
        return int(self.asset_returns.shape[2])

    @property
    def h(self) -> int:
        return int(self.asset_returns.shape[1])

    @property
    def k(self) -> int:
        if self.yield_tenors is None:
            return 0
        return int(len(self.yield_tenors))

    @property
    def b(self) -> int:
        if self.bei_tenors is None:
            return 0
        return int(len(self.bei_tenors))


def load_scenario_set(
    config: dict,
    *,
    load_yields: bool = True,
    load_bei: bool = True,
) -> ScenarioSet:
    """Load asset returns and optional curve matrices from a config."""

    asset_returns, asset_names = load_assets(config["assets"], config["horizon_years"])

    yield_config = config.get("yield") or {}
    if load_yields and yield_config.get("file"):
        yields, yield_tenors = globals()["load_yields"](yield_config, config["horizon_years"])
        assert yields.shape[0] == asset_returns.shape[0]
        assert yields.shape[1] == asset_returns.shape[1]
        assert yields.shape[2] == len(yield_tenors)
    else:
        yields, yield_tenors = None, None

    bei_config = config.get("bei") or {}
    if load_bei and bei_config.get("file"):
        bei, bei_tenors = globals()["load_yields"](bei_config, config["horizon_years"])
        assert bei.shape[0] == asset_returns.shape[0]
        assert bei.shape[1] == asset_returns.shape[1]
        assert bei.shape[2] == len(bei_tenors)
    else:
        bei, bei_tenors = None, None

    return ScenarioSet(
        asset_returns=asset_returns,
        asset_names=asset_names,
        horizon_years=int(config["horizon_years"]),
        yields=yields,
        yield_tenors=yield_tenors,
        bei=bei,
        bei_tenors=bei_tenors,
    )


def load_assets(asset_config: dict, horizon_years: int) -> tuple[np.ndarray, list[str]]:
    """Load asset sheets into an ``(M, T, N)`` return matrix."""

    filepath = Path(asset_config["file"])
    settings = dict(asset_config["settings"])
    assets = asset_config["sheets"]
    workbook = pd.ExcelFile(filepath)

    raw_data: dict[str, np.ndarray] = {}

    for asset_name, sheet_name in assets.items():
        try:
            df = pd.read_excel(workbook, sheet_name=sheet_name, **settings)
            values = df.to_numpy(dtype=float)
        except Exception as exc:
            raise RuntimeError(f"Could not load asset {asset_name!r} from {sheet_name!r}.") from exc

        if values.ndim != 2:
            raise ValueError(f"Asset {asset_name!r} is not a 2D sheet.")
        if values.shape[1] < horizon_years:
            raise ValueError(
                f"Asset {asset_name!r} has {values.shape[1]} year columns, "
                f"expected at least {horizon_years}."
            )

        raw_data[asset_name] = values[:, :horizon_years]

    scenario_counts = {name: values.shape[0] for name, values in raw_data.items()}
    if len(set(scenario_counts.values())) != 1:
        raise ValueError(f"Asset sheets have inconsistent scenario counts: {scenario_counts}")

    asset_names = list(raw_data)
    matrix = np.stack([raw_data[name] for name in asset_names], axis=2)

    return matrix.astype(float, copy=False), asset_names


def load_yields(yield_config: dict, horizon_years: int) -> tuple[np.ndarray, list[int]]:
    """Load yearly yield-curve sheets into an ``(M, T, K)`` matrix."""
    projection_years = int(yield_config["projection_years"])
    tenor_years = int(yield_config["tenor_years"])
    assert horizon_years <= projection_years

    filepath = Path(yield_config["file"])
    settings = dict(yield_config["settings"])
    sheet_template = yield_config["sheet_template"]
    first_sheet_year = int(yield_config.get("first_sheet_year", 1))
    workbook = pd.ExcelFile(filepath)

    yearly_curves: list[np.ndarray] = []

    for offset in range(horizon_years):
        year = first_sheet_year + offset
        sheet_name = sheet_template.format(year=year)
        try:
            df = pd.read_excel(workbook, sheet_name=sheet_name, **settings)
            values = df.to_numpy(dtype=float)
        except Exception as exc:
            raise RuntimeError(f"Could not load yield sheet {sheet_name!r}.") from exc

        if values.ndim != 2:
            raise ValueError(f"Yield sheet {sheet_name!r} is not a 2D sheet.")
        if values.shape[1] < tenor_years:
            raise ValueError(
                f"Yield sheet {sheet_name!r} has {values.shape[1]} tenor columns, "
                f"expected at least {tenor_years}."
            )

        yearly_curves.append(values[:, :tenor_years])

    scenario_counts = [curve.shape[0] for curve in yearly_curves]
    if len(set(scenario_counts)) != 1:
        raise ValueError(f"Yield sheets have inconsistent scenario counts: {scenario_counts}")

    matrix = np.stack(yearly_curves, axis=1).astype(float, copy=False)
    tenors = list(range(1, tenor_years + 1))

    return matrix, tenors
