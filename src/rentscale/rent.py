"""Rent's rule fitting: T = t * G**p, and locality steps between hierarchy levels."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


def _ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    xm, ym = x.mean(), y.mean()
    sxx = float(np.sum((x - xm) ** 2))
    if sxx == 0.0:
        raise ValueError("all x values identical; cannot fit a slope")
    slope = float(np.sum((x - xm) * (y - ym)) / sxx)
    return slope, float(ym - slope * xm)


@dataclass(frozen=True)
class PowerLawFit:
    """Least-squares fit of ``y = prefactor * x**exponent`` in log-log space."""

    exponent: float
    prefactor: float
    r2: float
    n: int
    residual_std: float
    exponent_ci: tuple[float, float] | None = None
    prefactor_ci: tuple[float, float] | None = None

    def predict(self, x):
        return self.prefactor * np.asarray(x, dtype=float) ** self.exponent

    def as_dict(self) -> dict:
        return asdict(self)


def fit_power_law(
    x, y, *, bootstrap: int = 0, ci: float = 0.95, seed: int | None = 0
) -> PowerLawFit:
    """Fit ``y = a * x**b`` by ordinary least squares on ``log y`` vs ``log x``.

    Non-positive or non-finite points are dropped. With ``bootstrap > 0`` a percentile
    confidence interval for the exponent and prefactor is computed by resampling points.
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.shape != y.shape:
        raise ValueError("x and y must have the same length")
    mask = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y > 0)
    x, y = x[mask], y[mask]
    if x.size < 2:
        raise ValueError("need at least two positive, finite points")
    if np.unique(x).size < 2:
        raise ValueError("need at least two distinct x values")
    lx, ly = np.log(x), np.log(y)
    slope, intercept = _ols(lx, ly)
    resid = ly - (intercept + slope * lx)
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    residual_std = float(np.sqrt(ss_res / max(x.size - 2, 1)))

    exp_ci = pre_ci = None
    if bootstrap and x.size >= 3:
        rng = np.random.default_rng(seed)
        slopes, inters = [], []
        n = x.size
        for _ in range(int(bootstrap)):
            idx = rng.integers(0, n, n)
            if np.unique(lx[idx]).size < 2:
                continue
            s, i = _ols(lx[idx], ly[idx])
            slopes.append(s)
            inters.append(i)
        if slopes:
            lo, hi = (1 - ci) / 2, 1 - (1 - ci) / 2
            q = np.quantile(slopes, [lo, hi])
            exp_ci = (float(q[0]), float(q[1]))
            q = np.exp(np.quantile(inters, [lo, hi]))
            pre_ci = (float(q[0]), float(q[1]))

    return PowerLawFit(
        exponent=slope,
        prefactor=float(np.exp(intercept)),
        r2=float(r2),
        n=int(x.size),
        residual_std=residual_std,
        exponent_ci=exp_ci,
        prefactor_ci=pre_ci,
    )


@dataclass(frozen=True)
class RentFit:
    """Rent's rule ``T = t * G**p``; ``p`` is the Rent exponent, ``t`` the coefficient."""

    p: float
    t: float
    r2: float
    n: int
    residual_std: float
    p_ci: tuple[float, float] | None = None
    t_ci: tuple[float, float] | None = None

    def predict(self, G):
        return self.t * np.asarray(G, dtype=float) ** self.p

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_power_law(cls, f: PowerLawFit) -> "RentFit":
        return cls(
            p=f.exponent,
            t=f.prefactor,
            r2=f.r2,
            n=f.n,
            residual_std=f.residual_std,
            p_ci=f.exponent_ci,
            t_ci=f.prefactor_ci,
        )

    def __str__(self) -> str:
        ci = f" [{self.p_ci[0]:.3f}, {self.p_ci[1]:.3f}]" if self.p_ci else ""
        return f"p = {self.p:.3f}{ci}  t = {self.t:.3g}  r2 = {self.r2:.3f}  n = {self.n}"


def fit_rent(G, T, **kwargs) -> RentFit:
    """Fit Rent's rule to gates ``G`` and terminals ``T``. See :func:`fit_power_law`."""
    return RentFit.from_power_law(fit_power_law(G, T, **kwargs))


def locality_steps(
    gates: Sequence[float], terminals: Sequence[float], names: Sequence[str] | None = None
) -> list[dict]:
    """Per-boundary locality statistics for consecutive levels ordered small -> large.

    For each pair of adjacent levels (l-1, l):

    * ``children``       = G_l / G_{l-1}, the number of level-(l-1) modules per level-l module
    * ``local_exponent`` = ln(T_l / T_{l-1}) / ln(G_l / G_{l-1}), the Rent exponent across
      that single boundary
    * ``lambda``         = T_l / (children * T_{l-1}), the fraction of the children's external
      capacity (or traffic) that leaves the parent; 1 = no locality exploited
    """
    G = np.asarray(gates, dtype=float)
    T = np.asarray(terminals, dtype=float)
    if G.shape != T.shape or G.ndim != 1:
        raise ValueError("gates and terminals must be 1-D and the same length")
    if names is None:
        names = [str(i) for i in range(G.size)]
    out = []
    for i in range(1, G.size):
        if G[i] <= 0 or G[i - 1] <= 0 or T[i - 1] <= 0:
            continue
        children = G[i] / G[i - 1]
        ratio_T = T[i] / T[i - 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            local_p = (
                float(np.log(ratio_T) / np.log(children))
                if ratio_T > 0 and children != 1.0
                else float("nan")
            )
        out.append(
            {
                "from": names[i - 1],
                "to": names[i],
                "children": float(children),
                "local_exponent": local_p,
                "lambda": float(T[i] / (children * T[i - 1])),
            }
        )
    return out
