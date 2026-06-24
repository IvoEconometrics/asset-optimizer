"""Scenario-based portfolio statistics."""

import numpy as np
import pandas as pd


def yearly_stats(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Arithmetic mean and average within-scenario covariance."""

    matrix = _as_matrix(matrix)
    _, _, n_assets = matrix.shape
    mu = np.mean(matrix, axis=(0, 1))

    covariances = []
    for scenario_index in range(matrix.shape[0]):
        cov = np.cov(matrix[scenario_index], rowvar=False, ddof=0)
        covariances.append(np.asarray(cov, dtype=float).reshape(n_assets, n_assets))

    sigma = np.mean(covariances, axis=0)
    return mu, sigma


def portfolio_series(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Return portfolio paths with shape ``(M, T)``."""

    matrix = _as_matrix(matrix)
    weights = _as_weights(weights, matrix.shape[2])
    return matrix @ weights


def arith_mean(matrix: np.ndarray, weights: np.ndarray, mu: np.ndarray | None = None) -> float:
    """Arithmetic mean portfolio return."""

    matrix = _as_matrix(matrix)
    weights = _as_weights(weights, matrix.shape[2])
    if mu is None:
        mu, _ = yearly_stats(matrix)
    return float(np.asarray(mu, dtype=float) @ weights)


def geo_mean(matrix: np.ndarray, weights: np.ndarray) -> float:
    """Mean annualized geometric return across scenarios."""

    paths = portfolio_series(matrix, weights)
    compounded = np.prod(1.0 + paths, axis=1)
    annualized = compounded ** (1.0 / paths.shape[1]) - 1.0
    return float(np.mean(annualized))


def vol(matrix: np.ndarray, weights: np.ndarray, sigma: np.ndarray | None = None) -> float:
    """Portfolio volatility from the average within-scenario covariance matrix."""

    matrix = _as_matrix(matrix)
    weights = _as_weights(weights, matrix.shape[2])
    if sigma is None:
        _, sigma = yearly_stats(matrix)
    sigma = np.asarray(sigma, dtype=float)
    return float(np.sqrt(weights @ sigma @ weights))


def compound_vol(matrix: np.ndarray, weights: np.ndarray) -> float:
    """Volatility of annualized compounded scenario outcomes."""

    paths = portfolio_series(matrix, weights)
    compounded = np.prod(1.0 + paths, axis=1)
    annualized = compounded ** (1.0 / paths.shape[1]) - 1.0
    return float(np.std(annualized, ddof=0))


def pct_pos_return(matrix: np.ndarray, weights: np.ndarray) -> float:
    """Percentage of year-scenario portfolio returns above zero."""

    paths = portfolio_series(matrix, weights)
    return float(np.round(100.0 * np.mean(paths > 0.0), 2))


def sharpe(
    matrix: np.ndarray,
    weights: np.ndarray,
    *,
    rf: float = 0.0,
    sigma: np.ndarray | None = None,
    use_geo_return: bool = True,
) -> float:
    """Sharpe ratio based on geometric or arithmetic return."""

    return_value = geo_mean(matrix, weights) if use_geo_return else arith_mean(matrix, weights)
    volatility = vol(matrix, weights, sigma=sigma)
    if volatility == 0.0:
        return 0.0
    return float((return_value - rf) / volatility)


def pct_neg_excess(
    weights: np.ndarray,
    benchmark_paths: np.ndarray,
    matrix: np.ndarray,
) -> tuple[float, float] | tuple[np.ndarray, np.ndarray]:
    """Share of terminal and year-scenario outcomes below a benchmark."""

    matrix = _as_matrix(matrix)
    benchmark_paths = _as_benchmark(benchmark_paths, matrix.shape[:2])
    weights = np.asarray(weights, dtype=float)
    one_portfolio = weights.ndim == 1

    if one_portfolio:
        weights = weights[None, :]
    if weights.shape[1] != matrix.shape[2]:
        raise ValueError(f"weights must have {matrix.shape[2]} columns, got {weights.shape[1]}.")

    port_paths = np.tensordot(matrix, weights.T, axes=(2, 0))
    port_terminal = np.prod(1.0 + port_paths, axis=1)
    bench_terminal = np.prod(1.0 + benchmark_paths, axis=1)[:, None]

    pct_terminal = np.round(100.0 * np.mean(port_terminal < bench_terminal, axis=0), 2)
    pct_overall = np.round(
        100.0 * np.mean(port_paths < benchmark_paths[:, :, None], axis=(0, 1)),
        2,
    )

    if one_portfolio:
        return float(pct_terminal[0]), float(pct_overall[0])
    return pct_terminal, pct_overall


def mean_neg_excess(
    weights: np.ndarray,
    benchmark_paths: np.ndarray,
    matrix: np.ndarray,
) -> float | np.ndarray:
    """Mean excess return where portfolio return is below the benchmark."""

    matrix = _as_matrix(matrix)
    benchmark_paths = _as_benchmark(benchmark_paths, matrix.shape[:2])
    weights = np.asarray(weights, dtype=float)
    one_portfolio = weights.ndim == 1

    if one_portfolio:
        weights = weights[None, :]
    if weights.shape[1] != matrix.shape[2]:
        raise ValueError(f"weights must have {matrix.shape[2]} columns, got {weights.shape[1]}.")

    port_paths = np.tensordot(matrix, weights.T, axes=(2, 0))
    excess_paths = port_paths - benchmark_paths[:, :, None]
    negative_mask = excess_paths < 0.0

    negative_sums = np.where(negative_mask, excess_paths, 0.0).sum(axis=(0, 1))
    negative_counts = negative_mask.sum(axis=(0, 1))
    mean_negative = np.divide(
        negative_sums,
        negative_counts,
        out=np.zeros_like(negative_sums, dtype=float),
        where=negative_counts > 0,
    )

    if one_portfolio:
        return float(mean_negative[0])
    return mean_negative


def evaluate_portfolio(
    matrix: np.ndarray,
    weights: np.ndarray,
    *,
    rf: float = 0.0,
    mu: np.ndarray | None = None,
    sigma: np.ndarray | None = None,
    benchmark_paths: np.ndarray | None = None,
    raw_matrix: np.ndarray | None = None,
) -> dict[str, float]:
    """Return the main reporting metrics for one portfolio."""

    stats = {
        "Arith_Return": arith_mean(matrix, weights, mu=mu),
        "Geo_Return": geo_mean(matrix, weights),
        "Volatility": vol(matrix, weights, sigma=sigma),
        "Compound_Vol": compound_vol(matrix, weights),
        "Sharpe": sharpe(matrix, weights, rf=rf, sigma=sigma),
        "Pct_Pos_Return": pct_pos_return(matrix, weights),
    }

    if benchmark_paths is not None and raw_matrix is not None:
        pct_terminal, pct_overall = pct_neg_excess(weights, benchmark_paths, raw_matrix)
        stats["Pct_Neg_Excess_Terminal"] = pct_terminal
        stats["Pct_Neg_Excess_Overall"] = pct_overall
        stats["Mean_Neg_Excess_Overall"] = mean_neg_excess(weights, benchmark_paths, raw_matrix)

    return stats


def asset_summary(matrix: np.ndarray, asset_names: list[str]) -> pd.DataFrame:
    """Return a compact table with per-asset mean and volatility."""

    matrix = _as_matrix(matrix)
    if len(asset_names) != matrix.shape[2]:
        raise ValueError(f"Expected {matrix.shape[2]} asset names, got {len(asset_names)}.")

    mu, sigma = yearly_stats(matrix)
    volatility = np.sqrt(np.diag(sigma))
    return pd.DataFrame(
        {
            "Asset": asset_names,
            "Arith_Return": mu,
            "Volatility": volatility,
        }
    )


def _as_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 3:
        raise ValueError(f"matrix must have shape (M, T, N), got {matrix.shape}.")
    return matrix


def _as_weights(weights: np.ndarray, n_assets: int) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (n_assets,):
        raise ValueError(f"weights must have shape {(n_assets,)}, got {weights.shape}.")
    return weights


def _as_benchmark(benchmark_paths: np.ndarray, expected_shape: tuple[int, int]) -> np.ndarray:
    benchmark_paths = np.asarray(benchmark_paths, dtype=float)
    if benchmark_paths.shape != expected_shape:
        raise ValueError(f"benchmark must have shape {expected_shape}, got {benchmark_paths.shape}.")
    return benchmark_paths
