"""Returns to scale, PUE model, dimension bounds, and the size trade-off model."""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from .rent import PowerLawFit, fit_power_law


def returns_to_scale(gamma: float, tol: float = 0.05) -> str:
    """Classify a cost exponent ``C ~ N**gamma``: ``increasing`` (economies of scale,
    gamma < 1), ``linear``, or ``diminishing`` (gamma > 1)."""
    if gamma < 1.0 - tol:
        return "increasing"
    if gamma > 1.0 + tol:
        return "diminishing"
    return "linear"


def allometric_fit(x, y, **kwargs) -> PowerLawFit:
    """Alias for :func:`rentscale.rent.fit_power_law` (cost or rate vs size)."""
    return fit_power_law(x, y, **kwargs)


# ----------------------------------------------------------------------------- PUE
def pue(total_energy: float, it_energy: float) -> float:
    if it_energy <= 0:
        raise ValueError("IT energy must be positive")
    return float(total_energy) / float(it_energy)


def pue_model(it_load, p_fixed: float, c: float):
    """``PUE(L) = 1 + (P_fixed + c L) / L``: fixed overhead amortized by load plus a
    proportional overhead; asymptote ``1 + c``."""
    L = np.asarray(it_load, dtype=float)
    return 1.0 + (p_fixed + c * L) / L


def fit_pue_model(it_load, pue_values) -> tuple[float, float]:
    """Fit ``(P_fixed, c)`` from ``(L, PUE)`` pairs via ``(PUE - 1) L = P_fixed + c L``."""
    L = np.asarray(it_load, dtype=float)
    P = np.asarray(pue_values, dtype=float)
    y = (P - 1.0) * L
    A = np.column_stack([np.ones_like(L), L])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[0]), float(coef[1])


# ----------------------------------------------------------------------------- dimension
def rent_dimension_bound(d: float) -> float:
    """Largest Rent exponent embeddable in ``d`` dimensions with bounded wire density
    (Ozaktas 1992): ``p_max = 1 - 1/d``."""
    return 1.0 - 1.0 / d


def dimension_from_rent(p: float) -> float:
    """``d_eff = 1 / (1 - p)``; infinite for ``p >= 1``."""
    if p >= 1.0:
        return math.inf
    return 1.0 / (1.0 - p)


def wbe_exponent(d: int) -> float:
    """Metabolic exponent of a space-filling supply network in ``d`` dimensions
    (West-Brown-Enquist / Banavar): ``d / (d + 1)`` (3/4 in 3D, 2/3 in 2D)."""
    return d / (d + 1.0)


def link_cost_scaling(p: float) -> dict:
    """Installed links vs system size under Rent's rule: linear for ``p < 1``,
    ``N log N`` for ``p = 1``."""
    return {"exponent": 1.0, "log_factor": bool(p >= 1.0)}


def wire_cost_scaling(p: float, d: float) -> dict:
    """Total wire length vs size when embedded in ``d`` dimensions: linear iff
    ``p < 1 - 1/d``; ``N log N`` at equality; ``N**(p + 1/d)`` above."""
    crit = 1.0 - 1.0 / d
    if p < crit - 1e-12:
        return {"exponent": 1.0, "log_factor": False}
    if abs(p - crit) <= 1e-12:
        return {"exponent": 1.0, "log_factor": True}
    return {"exponent": p + 1.0 / d, "log_factor": False}


# ----------------------------------------------------------------------------- size trade-off
def cost_per_unit(N, terms: Sequence[tuple[float, float]]):
    """``sum_i a_i N**(gamma_i - 1)`` for cost terms ``(a_i, gamma_i)``."""
    N = np.asarray(N, dtype=float)
    return sum(a * N ** (g - 1.0) for a, g in terms)


def optimal_size(terms: Sequence[tuple[float, float]], n_min: float = 1.0, n_max: float = 1e12) -> dict:
    """Minimize cost per unit over ``N`` in ``[n_min, n_max]`` (search in ``log N``).
    ``interior`` is True when the optimum is not at a bound."""
    from scipy.optimize import minimize_scalar

    lo, hi = math.log(n_min), math.log(n_max)
    res = minimize_scalar(lambda u: float(cost_per_unit(math.exp(u), terms)), bounds=(lo, hi), method="bounded")
    N = math.exp(res.x)
    interior = (res.x - lo) > 1e-3 * (hi - lo) and (hi - res.x) > 1e-3 * (hi - lo)
    return {"N_opt": N, "cost_per_unit": float(res.fun), "interior": bool(interior)}
