"""Run the US historical backtest through the generic lifecycle simulation."""

from functools import partial
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from asset_optimizer.loader import load_scenario_set
from asset_optimizer.simulation import run_lifecycle_simulation
from configs.us_backtest import BACKTEST_CONFIG
from scripts.rules.backtest_rules import backtest_lifecycle_rule, load_backtest_lifecycle_table


BACKTEST_LIFECYCLE_ASSETS = ("Bond_Return", "ILB_Return", "Equity_Return")

backtest_workbook = BACKTEST_CONFIG["assets"]["file"]
if not Path(backtest_workbook).exists():
    raise FileNotFoundError(
        f"Backtest workbook not found: {backtest_workbook}. "
        "Run python scripts/build_backtest_data.py first."
    )

scenario_set = load_scenario_set(BACKTEST_CONFIG, load_yields=False, load_bei=False)
lifecycle_table = load_backtest_lifecycle_table(PROJECT_ROOT / "data" / "lifecycle_tables.csv")
policy = partial(
    backtest_lifecycle_rule,
    table=lifecycle_table,
    lifecycle_assets=BACKTEST_LIFECYCLE_ASSETS,
    signal_name="Long_Interest_Rate",
    ma_window_years=5,
)

result = run_lifecycle_simulation(
    scenario_set,
    current_age=25,
    retirement_age=68,
    start_capital=100.0,
    annual_contribution=100.0,
    lifecycle_assets=BACKTEST_LIFECYCLE_ASSETS,
    benchmark_name="Inflation",
    policy=policy,
)

summary = pd.DataFrame(
    [
        {"Metric": "Years", "Value": result["years"]},
        {"Metric": "Final_Capital", "Value": float(result["final_capital"][0])},
        {"Metric": "Final_Real_Capital", "Value": float(result["final_real_capital"][0])},
    ]
)

output_path = PROJECT_ROOT / "outputs" / "backtest_results.csv"
output_path.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(output_path, index=False)

print(f"Wrote backtest results to: {output_path}")
print(summary.to_string(index=False))
