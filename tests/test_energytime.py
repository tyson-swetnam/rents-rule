import math

import numpy as np
import pytest

from rentscale import energytime as et
from rentscale import scaling as sc
from rentscale.rent import locality_step_from_p, p_from_locality_step


def test_dimensions_and_thresholds():
    assert et.rent_exponent(2.0) == 0.5
    assert et.communication_dimension(0.5) == 2.0
    assert et.locality_threshold(2.0) == 2.0  # D_w >= 2  <=>  p <= 1/2 on a 2-D layout
    assert et.locality_threshold(3.0) == pytest.approx(1.5)  # p <= 2/3 in 3-D
    # same bound as the Ozaktas embedding limit in rentscale.scaling
    for D_l in (2.0, 3.0):
        assert et.rent_exponent(et.locality_threshold(D_l)) == pytest.approx(sc.rent_dimension_bound(D_l))
    assert et.series_exponent(2.0, 2.0) == pytest.approx(0.0)
    assert et.series_exponent(2.0, 4.0) < 0 < et.series_exponent(2.0, 1.5)


def test_geometric_sum():
    assert et.geometric_sum(2.0, 0.0, 5) == 6.0
    assert et.geometric_sum(2.0, 1.0, 3) == 1 + 2 + 4 + 8
    assert et.geometric_sum(2.0, -1.0, 100) == pytest.approx(2.0)


def test_chip_regime_table_1():
    e = et.chip_exponents(2, 2, 2)
    assert (e.E_net, e.E_node, e.T_net, e.T_node) == (0.5, 0.5, 0.0, -0.5)
    assert e.energy_time == pytest.approx(0.5)  # N^(1/2) + N^(1/2)
    assert e.power == pytest.approx(0.5)  # measured 0.495 over 523 chips
    assert e.throughput == pytest.approx(1.0)  # measured 1.11 over 100 Intel chips
    assert e.per_node == pytest.approx(-0.5)  # increasing returns: better per transistor
    assert e.log_factor  # D_w = D_l/(D_l-1) exactly -> log N correction
    e3 = et.chip_exponents(3, 2, 1.5)
    assert e3.E_net == pytest.approx(2 / 3) and e3.T_node == pytest.approx(-1 / 3) and e3.power == pytest.approx(2 / 3)
    low = et.chip_exponents(2, 2, 1.5)  # D_w below the threshold: long wires dominate
    assert low.E_net == pytest.approx(1 / 1.5) and not low.log_factor


def test_datacenter_regime_end_of_increasing_returns():
    d = et.datacenter_exponents(D_l=2, p=0.25)
    assert d.E_net == 1.0 and d.E_node == 1.0 and d.T_net == 0.0 and d.T_node == 0.0
    assert d.power == pytest.approx(1.0) and d.per_node == pytest.approx(0.0) and not d.log_factor
    eq = et.datacenter_exponents(D_l=2, p=0.5)
    assert eq.E_net == 1.0 and eq.log_factor
    fb = et.datacenter_exponents(D_l=2, p=1.0)
    assert fb.E_net == pytest.approx(1.5)  # N^(p + 1/D_l): cable-metres grow superlinearly
    assert fb.per_node == pytest.approx(0.5)  # diminishing returns per node
    # agreement with the wire-cost regimes in rentscale.scaling
    for p in (0.25, 0.5, 0.8, 1.0):
        w = sc.wire_cost_scaling(p, 2)
        d = et.datacenter_exponents(2, p)
        assert d.E_net == pytest.approx(w["exponent"]) and d.log_factor == w["log_factor"]
    tapered = et.datacenter_exponents(D_l=2, p=0.8, oversubscription=2.0, lam=16)
    assert tapered.T_net == pytest.approx(math.log(2) / math.log(16))
    assert tapered.throughput == pytest.approx(1 - tapered.T_net)
    with pytest.raises(ValueError):
        et.datacenter_exponents(2, 0.8, oversubscription=2.0)


def test_total_wire_length_regimes_numerically():
    lam = 2.0
    N1, N2 = 2.0**20, 2.0**24
    # chip regime, convergent (D_w = 4): L ~ N^(1/2) -> x16 in N gives x4
    r = et.total_wire_length(N2, lam, 2, 4, shrink=True) / et.total_wire_length(N1, lam, 2, 4, shrink=True)
    assert r == pytest.approx(4.0, rel=0.02)
    # data-center regime with locality (p = 0.25): L ~ N -> x16
    r = et.total_wire_length(N2, lam, 2, 4) / et.total_wire_length(N1, lam, 2, 4)
    assert r == pytest.approx(16.0, rel=0.03)
    # full bisection on a 2-D floor (p = 1): L ~ N^(3/2) -> x64
    r = et.total_wire_length(N2, lam, 2, 1) / et.total_wire_length(N1, lam, 2, 1)
    assert r == pytest.approx(64.0, rel=0.05)
    # link count: linear for p < 1, N log N at p = 1
    assert et.total_links(N2, lam, 4) / et.total_links(N1, lam, 4) == pytest.approx(16.0, rel=0.02)
    assert et.total_links(N2, lam, 1) / et.total_links(N1, lam, 1) == pytest.approx(16 * 25 / 21)


def test_mammal_regime():
    wbe = et.mammal_exponents(3, 2.0)
    assert wbe.E_net == 0.0 and wbe.E_node == 1.0 and wbe.T_net == 0.0
    opt = et.mammal_exponents(3, et.OPTIMAL_DR_MAMMAL)
    assert opt.E_net == pytest.approx(2 / et.OPTIMAL_DR_MAMMAL - 1)  # negative with l_0, u_0 fixed
    assert opt.T_net == pytest.approx(1 - 2 / et.OPTIMAL_DR_MAMMAL)
    case2 = et.mammal_exponents(3, 3.5)  # above 4 D_l / (1 + D_l) = 3
    assert case2.E_net == pytest.approx(1 / 3 - 2 / 3.5)


def test_locality_step_closed_forms():
    assert locality_step_from_p(1.0, 8) == 1.0
    assert locality_step_from_p(0.5, 4) == pytest.approx(0.5)
    for p in (0.2, 0.5, 0.9):
        assert p_from_locality_step(locality_step_from_p(p, 16), 16) == pytest.approx(p)
    # the DGX-like example: lambda = 0.1037 with 8 children -> local p = -0.083 (as printed by the demo)
    assert p_from_locality_step(0.1037, 8) == pytest.approx(-0.09, abs=0.01)
    assert np.isfinite(p_from_locality_step(1e-3, 26))


def test_summary_table_shape():
    df = et.summary_table()
    assert len(df) == 8 and {"chip", "datacenter", "mammal"} == set(df.regime)
    assert df.loc[df.case.str.startswith("chips, Dennard"), "power"].iloc[0] == pytest.approx(0.5)
