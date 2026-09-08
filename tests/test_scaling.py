import math

import numpy as np
import pytest

from rentscale import scaling as sc


def test_returns_classification():
    assert sc.returns_to_scale(0.75) == "increasing"
    assert sc.returns_to_scale(1.0) == "linear"
    assert sc.returns_to_scale(1.3) == "diminishing"


def test_pue_model_and_fit():
    L = np.array([100.0, 200.0, 400.0, 800.0])
    P = sc.pue_model(L, p_fixed=50.0, c=0.1)
    assert np.all(np.diff(P) < 0)  # falls with load
    assert P[-1] == pytest.approx(1.1 + 50 / 800)
    pf, c = sc.fit_pue_model(L, P)
    assert pf == pytest.approx(50.0) and c == pytest.approx(0.1)
    assert sc.pue(1200, 1000) == pytest.approx(1.2)


def test_dimension_bounds():
    assert sc.rent_dimension_bound(2) == pytest.approx(0.5)
    assert sc.rent_dimension_bound(3) == pytest.approx(2 / 3)
    assert sc.dimension_from_rent(0.5) == pytest.approx(2.0)
    assert sc.dimension_from_rent(2 / 3) == pytest.approx(3.0)
    assert math.isinf(sc.dimension_from_rent(1.0))
    assert sc.wbe_exponent(3) == pytest.approx(0.75)
    assert sc.wbe_exponent(2) == pytest.approx(2 / 3)


def test_cost_scaling_regimes():
    assert sc.link_cost_scaling(0.8) == {"exponent": 1.0, "log_factor": False}
    assert sc.link_cost_scaling(1.0)["log_factor"] is True
    assert sc.wire_cost_scaling(0.4, 2) == {"exponent": 1.0, "log_factor": False}
    assert sc.wire_cost_scaling(0.5, 2)["log_factor"] is True
    assert sc.wire_cost_scaling(0.8, 2)["exponent"] == pytest.approx(1.3)


def test_optimal_size_interior():
    # economies of scale (gamma 0.8) vs diseconomies (gamma 1.3): interior optimum
    res = sc.optimal_size([(1.0, 0.8), (1e-3, 1.3)], 1, 1e9)
    assert res["interior"]
    N = res["N_opt"]
    # analytic: d/dN [N^-0.2 + 1e-3 N^0.3] = 0 -> N^0.5 = 0.2/(3e-4) -> N = (666.7)^2
    assert N == pytest.approx((0.2 / 3e-4) ** 2, rel=0.02)
    res2 = sc.optimal_size([(1.0, 0.8)], 1, 1e9)
    assert not res2["interior"]
