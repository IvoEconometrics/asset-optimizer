"""Create the portfolio input workbook."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from asset_optimizer.loader import load_scenario_set
from asset_optimizer.template import create_input_template
from configs.ultimo_2025_assets import SCENARIO_CONFIG


scenario_set = load_scenario_set(SCENARIO_CONFIG)
output_path = create_input_template(PROJECT_ROOT / "inputs" / "portfolio_input.xlsx", scenario_set)

print(f"Wrote portfolio input workbook to: {output_path}")
print(f"Assets ({len(scenario_set.asset_names)}):")
for asset_name in scenario_set.asset_names:
    print(f"- {asset_name}")
