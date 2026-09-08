"""Self-similar traffic: exact fractional Gaussian noise synthesis and Hurst / spectral
estimators (R/S, aggregated variance, DFA, Welch periodogram)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class HurstResult:
    H: float
    method: str
    r2: float
    scales: np.ndarray
    statistic: np.ndarray
    slope: float
    extra: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.method}: H = {self.H:.3f} (r2 = {self.r2:.3f}, {self.scales.size} scales)"


# ----------------------------------------------------------------------------- synthesis
def fgn_autocovariance(k, H: float) -> np.ndarray:
    k = np.abs(np.asarray(k, dtype=float))
    return 0.5 * ((k + 1) ** (2 * H) - 2 * k ** (2 * H) + np.abs(k - 1) ** (2 * H))


def fgn(n: int, H: float, seed: int | None = None, scale: float = 1.0) -> np.ndarray:
    """Exact fractional Gaussian noise (unit variance) by Davies-Harte circulant embedding.
    ``H = 0.5`` is white noise; ``0.5 < H < 1`` is long-range dependent."""
    if not 0.0 < H < 1.0:
        raise ValueError("H must be in (0, 1)")
    if n < 2:
        raise ValueError("n must be >= 2")
    rng = np.random.default_rng(seed)
    m = 2 * n
    gamma = fgn_autocovariance(np.arange(n + 1), H)
    row = np.concatenate([gamma, gamma[-2:0:-1]])  # length 2n circulant first row
    lam = np.fft.fft(row).real
    lam = np.clip(lam, 0.0, None)  # tiny negatives from rounding
    w = np.zeros(m, dtype=complex)
    z0 = rng.standard_normal(2)
    w[0] = np.sqrt(lam[0] / m) * z0[0]
    w[n] = np.sqrt(lam[n] / m) * z0[1]
    re = rng.standard_normal(n - 1)
    im = rng.standard_normal(n - 1)
    w[1:n] = np.sqrt(lam[1:n] / (2 * m)) * (re + 1j * im)
    w[n + 1 :] = np.conj(w[1:n][::-1])
    x = np.fft.fft(w).real[:n]
    return scale * x


def beta_from_H(H: float) -> float:
    """Spectral exponent ``S(f) ~ f**(-beta)`` of fGn: ``beta = 2H - 1``."""
    return 2.0 * H - 1.0


def H_from_beta(beta: float) -> float:
    return (beta + 1.0) / 2.0


def H_from_tail_index(alpha: float) -> float:
    """Taqqu's theorem: superposed ON/OFF sources with heavy-tailed periods of tail index
    ``1 < alpha < 2`` give ``H = (3 - alpha) / 2``."""
    return (3.0 - alpha) / 2.0


# ----------------------------------------------------------------------------- helpers
def _clean(x) -> np.ndarray:
    x = np.asarray(x, dtype=float).ravel()
    x = x[np.isfinite(x)]
    if x.size < 64:
        raise ValueError("need at least 64 finite samples")
    return x


def _log_sizes(lo: int, hi: int, num: int) -> np.ndarray:
    if hi < lo:
        return np.array([], dtype=int)
    s = np.unique(np.floor(np.logspace(np.log10(lo), np.log10(hi), num)).astype(int))
    return s[(s >= lo) & (s <= hi)]


def _loglog_slope(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    lx, ly = np.log(x), np.log(y)
    slope, intercept = np.polyfit(lx, ly, 1)
    pred = intercept + slope * lx
    ss_res = float(np.sum((ly - pred) ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return float(slope), float(r2)


# ----------------------------------------------------------------------------- estimators
def rs_hurst(x, min_size: int = 16, max_size: int | None = None, num: int = 20) -> HurstResult:
    """Rescaled-range (R/S) estimator: ``E[R/S](n) ~ n**H``."""
    x = _clean(x)
    n = x.size
    if max_size is None:
        max_size = n // 2
    sizes = _log_sizes(min_size, max_size, num)
    if sizes.size < 3:
        raise ValueError("series too short for the requested window range")
    stats, used = [], []
    for s in sizes:
        k = n // s
        seg = x[: k * s].reshape(k, s)
        dev = seg - seg.mean(axis=1, keepdims=True)
        y = np.cumsum(dev, axis=1)
        R = y.max(axis=1) - y.min(axis=1)
        S = seg.std(axis=1)
        ok = S > 0
        if not ok.any():
            continue
        stats.append(float(np.mean(R[ok] / S[ok])))
        used.append(int(s))
    used_a, stats_a = np.array(used), np.array(stats)
    slope, r2 = _loglog_slope(used_a, stats_a)
    return HurstResult(H=slope, method="rs", r2=r2, scales=used_a, statistic=stats_a, slope=slope)


def aggregated_variance_hurst(
    x, min_size: int = 1, max_size: int | None = None, num: int = 20, min_blocks: int = 8
) -> HurstResult:
    """Aggregated-variance estimator: ``Var(X^(m)) ~ m**(2H-2)``."""
    x = _clean(x)
    n = x.size
    if max_size is None:
        max_size = n // min_blocks
    sizes = _log_sizes(min_size, max_size, num)
    vars_, used = [], []
    for m in sizes:
        k = n // m
        if k < min_blocks:
            continue
        blocks = x[: k * m].reshape(k, m).mean(axis=1)
        v = float(blocks.var(ddof=1))
        if v > 0:
            vars_.append(v)
            used.append(int(m))
    if len(used) < 3:
        raise ValueError("series too short")
    used_a, vars_a = np.array(used), np.array(vars_)
    slope, r2 = _loglog_slope(used_a, vars_a)
    return HurstResult(
        H=1.0 + slope / 2.0, method="aggvar", r2=r2, scales=used_a, statistic=vars_a, slope=slope
    )


def dfa_hurst(
    x, order: int = 1, min_size: int = 16, max_size: int | None = None, num: int = 20
) -> HurstResult:
    """Detrended fluctuation analysis: ``F(n) ~ n**alpha``; ``alpha = H`` for fGn-like
    (stationary) series. Windows are taken from both ends of the profile."""
    x = _clean(x)
    n = x.size
    y = np.cumsum(x - x.mean())
    if max_size is None:
        max_size = n // 4
    sizes = _log_sizes(min_size, max_size, num)
    F, used = [], []
    for s in sizes:
        k = n // s
        if k < 2:
            continue
        t = np.arange(s, dtype=float)
        V = np.vander(t, order + 1)
        f2 = []
        for seg in (y[: k * s].reshape(k, s), y[n - k * s :].reshape(k, s)):
            coef, *_ = np.linalg.lstsq(V, seg.T, rcond=None)
            resid = seg - (V @ coef).T
            f2.append(np.mean(resid**2, axis=1))
        F.append(float(np.sqrt(np.mean(np.concatenate(f2)))))
        used.append(int(s))
    if len(used) < 3:
        raise ValueError("series too short")
    used_a, F_a = np.array(used), np.array(F)
    slope, r2 = _loglog_slope(used_a, F_a)
    return HurstResult(H=slope, method=f"dfa{order}", r2=r2, scales=used_a, statistic=F_a, slope=slope)


def periodogram_hurst(
    x, fmax: float = 0.1, nperseg: int | None = None, nbins: int = 20
) -> HurstResult:
    """Welch periodogram, log-binned, fitted for ``f <= fmax`` (cycles per sample):
    ``S(f) ~ f**(1-2H)``. Returns ``beta`` in ``extra``."""
    from scipy.signal import welch

    x = _clean(x)
    n = x.size
    if nperseg is None:
        nperseg = int(max(64, min(n // 8, 8192)))
    f, P = welch(x - x.mean(), fs=1.0, nperseg=nperseg, detrend="constant", scaling="density")
    m = (f > 0) & (f <= fmax) & (P > 0)
    if m.sum() < 8:
        raise ValueError("too few spectral points below fmax; lower nperseg or raise fmax")
    lf, lp = np.log10(f[m]), np.log10(P[m])
    edges = np.linspace(lf.min(), lf.max(), nbins + 1)
    idx = np.clip(np.digitize(lf, edges) - 1, 0, nbins - 1)
    bf = np.array([lf[idx == i].mean() for i in range(nbins) if np.any(idx == i)])
    bp = np.array([lp[idx == i].mean() for i in range(nbins) if np.any(idx == i)])
    slope, intercept = np.polyfit(bf, bp, 1)
    pred = intercept + slope * bf
    ss_res = float(np.sum((bp - pred) ** 2))
    ss_tot = float(np.sum((bp - bp.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    beta = -float(slope)
    return HurstResult(
        H=H_from_beta(beta),
        method="periodogram",
        r2=r2,
        scales=10.0**bf,
        statistic=10.0**bp,
        slope=float(slope),
        extra={"beta": beta, "nperseg": nperseg},
    )


def hurst_summary(x) -> dict[str, float]:
    """All estimators at default settings; NaN where an estimator fails."""
    out: dict[str, float] = {}
    for name, fn in (
        ("rs", rs_hurst),
        ("aggvar", aggregated_variance_hurst),
        ("dfa1", dfa_hurst),
        ("periodogram", periodogram_hurst),
    ):
        try:
            res = fn(x)
            out[name] = float(res.H)
            if name == "periodogram":
                out["beta"] = float(res.extra["beta"])
        except Exception:
            out[name] = float("nan")
    vals = [v for k, v in out.items() if k != "beta" and np.isfinite(v)]
    out["mean"] = float(np.mean(vals)) if vals else float("nan")
    return out
