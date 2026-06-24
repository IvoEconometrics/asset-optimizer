"""Pure mean-variance frontier solver."""

import numpy as np
import pandas as pd

try:
    import cvxpy as cp
except ImportError:
    cp = None


class Solver:
    def __init__(
        self,
        mu,
        Sigma,
        lb,
        ub,
        asset_names,
        group_A=None,
        group_lb=None,
        group_ub=None,
        solver=None,
    ):
        if cp is None:
            raise ImportError("Install cvxpy to use asset_optimizer.solver.Solver.")

        self.mu = np.asarray(mu, dtype=float)
        self.Sigma = np.asarray(Sigma, dtype=float)
        self.lb = np.asarray(lb, dtype=float)
        self.ub = np.asarray(ub, dtype=float)
        self.asset_names = list(asset_names)
        self.N = len(self.asset_names)
        self.solver = solver if solver else cp.GUROBI

        assert self.mu.shape == (self.N,)
        assert self.Sigma.shape == (self.N, self.N)
        assert self.lb.shape == self.ub.shape == (self.N,)

        provided = [group_A is not None, group_lb is not None, group_ub is not None]
        assert all(provided) or not any(provided)

        if not any(provided):
            self.group_A = None
            self.group_lb = None
            self.group_ub = None
        else:
            self.group_A = np.asarray(group_A, dtype=float)
            self.group_lb = np.asarray(group_lb, dtype=float)
            self.group_ub = np.asarray(group_ub, dtype=float)

            G = self.group_A.shape[0]
            assert self.group_A.ndim == 2 and self.group_A.shape[1] == self.N
            assert self.group_lb.shape == self.group_ub.shape == (G,)

    def solve_frontier(self, n_lambdas=250, step: float | None = 0.025):
        assert step is None or step > 0.0
        ok = ("optimal", "optimal_inaccurate")

        w_gmv, gmv_problem = self._build_problem(
            lambda w: cp.Minimize(cp.quad_form(w, self.Sigma)),
            step,
        )
        gmv_problem.solve(solver=self.solver)
        assert gmv_problem.status in ok and w_gmv.value is not None
        w_gmv = np.asarray(w_gmv.value, dtype=float)

        w_max, max_problem = self._build_problem(
            lambda w: cp.Maximize(self.mu @ w),
            step,
        )
        max_problem.solve(solver=self.solver)
        assert max_problem.status in ok and w_max.value is not None
        w_max = np.asarray(w_max.value, dtype=float)

        risk_gmv = float(w_gmv @ self.Sigma @ w_gmv)
        risk_max = float(w_max @ self.Sigma @ w_max)

        lam_gmv = abs(float(self.mu @ w_gmv) / (2.0 * risk_gmv + 1e-12))
        lam_max = abs(float(self.mu @ w_max) / (2.0 * risk_max + 1e-12))
        lam_low, lam_high = sorted([max(lam_gmv, 1e-8), max(lam_max, 1e-8)])

        lam_param = cp.Parameter(nonneg=True)
        w, problem = self._build_problem(
            lambda w: cp.Maximize(self.mu @ w - lam_param * cp.quad_form(w, self.Sigma)),
            step,
        )

        lambdas = np.concatenate(
            (
                [0.0],
                np.logspace(
                    np.log10(lam_low) - 1.0,
                    np.log10(lam_high) + 1.0,
                    n_lambdas,
                ),
            )
        )

        rows = []
        seen = set()

        gmv_weights = np.round(w_gmv, 4)
        rows.append(self._weights_to_row(gmv_weights))
        seen.add(tuple(gmv_weights))

        for lam in np.sort(lambdas)[::-1]:
            lam_param.value = lam

            try:
                problem.solve(solver=self.solver, warm_start=True)
            except Exception:
                continue

            if problem.status not in ok or w.value is None:
                continue

            weights = np.round(np.asarray(w.value, dtype=float), 4)
            key = tuple(weights)

            if key in seen:
                continue

            seen.add(key)
            rows.append(self._weights_to_row(weights))

        frontier_df = pd.DataFrame(rows)
        frontier_df = frontier_df.sort_values("Arith_Return").reset_index(drop=True)
        return frontier_df

    def _build_problem(self, objective_builder, step: float | None):
        if step is not None:
            k = cp.Variable(self.N, integer=True)
            w = step * k
            constraints = [k >= 0]
        else:
            w = cp.Variable(self.N)
            constraints = []

        constraints.extend(
            [
                cp.sum(w) == 1.0,
                w >= self.lb,
                w <= self.ub,
            ]
        )

        if self.group_A is not None:
            constraints.append(self.group_A @ w >= self.group_lb)
            constraints.append(self.group_A @ w <= self.group_ub)

        problem = cp.Problem(objective_builder(w), constraints)
        return w, problem

    def _weights_to_row(self, weights):
        row = {name: weights[i] for i, name in enumerate(self.asset_names)}
        row["Arith_Return"] = float(self.mu @ weights)
        row["Volatility"] = float(np.sqrt(weights @ self.Sigma @ weights))
        return row
