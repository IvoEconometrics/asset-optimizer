"""Run all portfolio input workbooks and write output workbooks."""

from pathlib import Path
import sys

import cvxpy as cp
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from asset_optimizer.loader import load_scenario_set
from asset_optimizer.solver import Solver
from asset_optimizer.stats import evaluate_portfolio, mean_neg_excess, pct_neg_excess, yearly_stats
from asset_optimizer.template import load_input_template, write_output_workbook
from configs.ultimo_2025_colab import SCENARIO_CONFIG


CASE_SPECS = {
    "APF_h5_no_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APF_h5_no_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APF_h5_no_inflation.xlsx",
    ),
    "APF_h5_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APF_h5_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APF_h5_inflation.xlsx",
    ),
    "APF_h15_no_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APF_h15_no_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APF_h15_no_inflation.xlsx",
    ),
    "APF_h15_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APF_h15_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APF_h15_inflation.xlsx",
    ),
    "APL_h5_no_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APL_h5_no_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APL_h5_no_inflation.xlsx",
    ),
    "APL_h5_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APL_h5_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APL_h5_inflation.xlsx",
    ),
    "APL_h15_no_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APL_h15_no_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APL_h15_no_inflation.xlsx",
    ),
    "APL_h15_inflation": (
        PROJECT_ROOT / "inputs" / "portfolio_input_APL_h15_inflation.xlsx",
        PROJECT_ROOT / "outputs" / "portfolio_output_APL_h15_inflation.xlsx",
    ),
}


scenario_set = load_scenario_set(SCENARIO_CONFIG, load_yields=False, load_bei=False)

for case_name, (input_path, output_path) in CASE_SPECS.items():
    inputs = load_input_template(input_path, scenario_set)
    horizon_years = int(inputs["settings"].loc["horizon_years"])
    matrix_h = scenario_set.asset_returns[:, :horizon_years, :]

    benchmark_weights = inputs["benchmark"].reindex(scenario_set.asset_names).fillna(0.0).to_numpy(dtype=float)
    benchmark_h = matrix_h @ benchmark_weights
    selected_matrix = matrix_h - benchmark_h[:, :, None]

    mu, sigma = yearly_stats(selected_matrix)
    portfolios = inputs["portfolios"].reindex(scenario_set.asset_names).fillna(0.0)

    portfolio_rows = []
    for portfolio_name in portfolios.columns:
        weights = portfolios[portfolio_name].to_numpy(dtype=float)
        stats = evaluate_portfolio(
            selected_matrix,
            weights,
            rf=0.0,
            mu=mu,
            sigma=sigma,
            benchmark_paths=benchmark_h,
            raw_matrix=matrix_h,
        )
        portfolio_rows.append({"Portfolio": portfolio_name, "Weight_Sum": weights.sum(), **stats})
    portfolio_stats = pd.DataFrame(portfolio_rows)

    bounds = inputs["asset_bounds"].reindex(scenario_set.asset_names)
    lb = bounds["Min"].fillna(0.0).to_numpy(dtype=float)
    ub = bounds["Max"].fillna(1.0).to_numpy(dtype=float)

    group_bounds = inputs["group_bounds"]
    active_groups = group_bounds[group_bounds[["Min", "Max"]].notna().any(axis=1)]
    if active_groups.empty:
        group_A = group_lb = group_ub = None
    else:
        memberships = inputs["group_memberships"].reindex(scenario_set.asset_names)
        group_keys = list(active_groups.index)
        group_A = memberships[group_keys].apply(pd.to_numeric, errors="coerce").fillna(0.0).T.to_numpy(dtype=float)
        group_lb = active_groups["Min"].fillna(0.0).to_numpy(dtype=float)
        group_ub = active_groups["Max"].fillna(1.0).to_numpy(dtype=float)

    frontier = Solver(
        mu,
        sigma,
        lb,
        ub,
        scenario_set.asset_names,
        group_A=group_A,
        group_lb=group_lb,
        group_ub=group_ub,
        solver=cp.GUROBI,
    ).solve_frontier(
        n_lambdas=int(inputs["settings"].get("frontier_points", 25)),
        step=float(inputs["settings"].get("step_size", 0.025)),
    )

    frontier_weights = frontier[scenario_set.asset_names].to_numpy(dtype=float)
    frontier["Pct_Neg_Excess_Terminal"], frontier["Pct_Neg_Excess_Overall"] = pct_neg_excess(
        frontier_weights,
        benchmark_h,
        matrix_h,
    )
    frontier["Mean_Neg_Excess_Overall"] = mean_neg_excess(frontier_weights, benchmark_h, matrix_h)

    frontier_metric_rows = []
    for idx, weights in enumerate(frontier_weights, start=1):
        metrics = evaluate_portfolio(
            selected_matrix,
            weights,
            rf=0.0,
            mu=mu,
            sigma=sigma,
            benchmark_paths=benchmark_h,
            raw_matrix=matrix_h,
        )
        frontier_metric_rows.append({"Portfolio": f"Frontier {idx}", "Weight_Sum": weights.sum(), **metrics})
    frontier_metrics = pd.DataFrame(frontier_metric_rows).set_index("Portfolio")
    for metric in frontier_metrics.columns:
        frontier[metric] = frontier_metrics[metric].to_numpy(dtype=float)

    write_output_workbook(input_path, output_path, portfolios, portfolio_stats, frontier=frontier)
    print(f"Wrote {case_name}: {output_path}")
