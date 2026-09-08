import numpy as np
import pytest

from rentscale import hurst

N = 1 << 14


def test_fgn_statistics():
    x = hurst.fgn(N, 0.8, seed=3)
    assert x.shape == (N,)
    # the sample mean of LRD noise converges as n**(H-1): allow 3 sigma
    assert abs(x.mean()) < 3 * N ** (0.8 - 1)
    assert x.var() == pytest.approx(1.0, abs=0.15)
    # lag-1 autocorrelation of fGn: rho(1) = 2**(2H-1) - 1
    rho1 = np.corrcoef(x[:-1], x[1:])[0, 1]
    assert rho1 == pytest.approx(2 ** (2 * 0.8 - 1) - 1, abs=0.05)
    w = hurst.fgn(N, 0.5, seed=3)
    assert abs(np.corrcoef(w[:-1], w[1:])[0, 1]) < 0.05


def test_fgn_rejects_bad_H():
    with pytest.raises(ValueError):
        hurst.fgn(100, 1.0)
    with pytest.raises(ValueError):
        hurst.fgn(100, 0.0)


@pytest.mark.parametrize("H", [0.5, 0.7, 0.9])
def test_estimators_recover_H(H):
    x = hurst.fgn(N, H, seed=11)
    tol = {"rs": 0.12, "aggvar": 0.1, "dfa1": 0.1, "periodogram": 0.1}
    res = {
        "rs": hurst.rs_hurst(x),
        "aggvar": hurst.aggregated_variance_hurst(x),
        "dfa1": hurst.dfa_hurst(x),
        "periodogram": hurst.periodogram_hurst(x),
    }
    for name, r in res.items():
        assert abs(r.H - H) < tol[name], f"{name}: {r.H:.3f} vs {H}"
        if not (name == "periodogram" and H == 0.5):  # a flat spectrum has no slope to explain
            assert r.r2 > 0.8, f"{name}: r2 = {r.r2:.3f}"
    assert res["periodogram"].extra["beta"] == pytest.approx(hurst.beta_from_H(H), abs=0.2)


def test_summary_and_helpers():
    s = hurst.hurst_summary(hurst.fgn(N, 0.75, seed=5))
    assert set(s) >= {"rs", "aggvar", "dfa1", "periodogram", "beta", "mean"}
    assert abs(s["mean"] - 0.75) < 0.08
    assert hurst.H_from_tail_index(1.5) == pytest.approx(0.75)
    assert hurst.H_from_beta(hurst.beta_from_H(0.6)) == pytest.approx(0.6)


def test_short_series_rejected():
    with pytest.raises(ValueError):
        hurst.rs_hurst(np.random.default_rng(0).normal(size=32))
