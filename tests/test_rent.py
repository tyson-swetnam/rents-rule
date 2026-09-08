import numpy as np
import pytest

from rentscale.rent import fit_power_law, fit_rent, locality_steps


def test_fit_recovers_exponent_and_prefactor():
    G = np.logspace(1, 9, 40)
    T = 3.0 * G**0.7
    fit = fit_rent(G, T)
    assert fit.p == pytest.approx(0.7, abs=1e-9)
    assert fit.t == pytest.approx(3.0, rel=1e-9)
    assert fit.r2 == pytest.approx(1.0)
    assert fit.n == 40


def test_fit_with_noise_and_bootstrap_ci_covers_truth():
    rng = np.random.default_rng(0)
    G = np.logspace(2, 10, 60)
    T = 2.0 * G**0.6 * np.exp(rng.normal(0, 0.15, G.size))
    fit = fit_rent(G, T, bootstrap=400, seed=1)
    assert abs(fit.p - 0.6) < 0.03
    lo, hi = fit.p_ci
    assert lo < 0.6 < hi
    assert fit.residual_std == pytest.approx(0.15, abs=0.05)


def test_fit_drops_nonpositive_points():
    fit = fit_power_law([1, 10, 100, 0, -5], [1, 10, 100, 5, 5])
    assert fit.n == 3
    assert fit.exponent == pytest.approx(1.0)


def test_fit_rejects_degenerate_input():
    with pytest.raises(ValueError):
        fit_rent([5, 5, 5], [1, 2, 3])
    with pytest.raises(ValueError):
        fit_rent([1], [1])


def test_locality_steps_full_bisection_and_taper():
    # full bisection: T doubles with G (k=2) -> lambda 1, local p = 1
    steps = locality_steps([1, 2, 4], [1, 2, 4], names=["a", "b", "c"])
    assert len(steps) == 2
    assert steps[0]["children"] == 2
    assert steps[0]["lambda"] == pytest.approx(1.0)
    assert steps[0]["local_exponent"] == pytest.approx(1.0)
    # 2:1 taper: 4 children, T doubles -> lambda 0.5, local p = 0.5
    steps = locality_steps([1, 4], [1, 2])
    assert steps[0]["lambda"] == pytest.approx(0.5)
    assert steps[0]["local_exponent"] == pytest.approx(0.5)
    # DGX-like: 8 children, T halves -> lambda 1/16, negative local exponent
    steps = locality_steps([1, 8], [64, 32])
    assert steps[0]["lambda"] == pytest.approx(1 / 16)
    assert steps[0]["local_exponent"] == pytest.approx(np.log(0.5) / np.log(8))
