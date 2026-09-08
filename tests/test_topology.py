import numpy as np
import pytest

from rentscale import topology as tp


def test_fat_tree_counts_and_rent_exponent_is_one():
    k = 4
    G = tp.fat_tree(k)
    kinds = [d["kind"] for _, d in G.nodes(data=True)]
    assert kinds.count("host") == k**3 // 4 == 16
    assert kinds.count("core") == (k // 2) ** 2 == 4
    assert kinds.count("agg") == kinds.count("edge") == k * k // 2 == 8
    assert G.number_of_edges() == 3 * k**3 // 4  # 16 host + 16 edge-agg + 16 agg-core
    for n, d in G.nodes(data=True):
        if d["kind"] != "host":
            assert G.degree(n) == k
    pts = tp.rent_points(G, tp.fat_tree_modules(G))
    fit = tp.fit_rent_points(pts)
    assert fit.p == pytest.approx(1.0, abs=1e-9)
    assert fit.t == pytest.approx(1.0, rel=1e-9)
    root = pts[pts.level == "tree"].iloc[0]
    assert root.links == 0  # the whole tree has no external links


@pytest.mark.parametrize("k", [6, 8])
def test_fat_tree_larger(k):
    G = tp.fat_tree(k)
    pts = tp.rent_points(G, tp.fat_tree_modules(G))
    assert tp.fit_rent_points(pts).p == pytest.approx(1.0, abs=1e-9)
    assert pts[pts.level == "pod"].gates.iloc[0] == k * k / 4


def test_tapered_exponent_closed_form():
    assert tp.tapered_exponent(16, 1) == pytest.approx(1.0)
    assert tp.tapered_exponent(16, 2) == pytest.approx(0.75)
    assert tp.tapered_exponent(32, 2) == pytest.approx(0.8)
    assert tp.tapered_exponent(16, 16) == pytest.approx(0.0)


@pytest.mark.parametrize("r", [1, 2, 4])
def test_hierarchical_tree_graph_matches_analytic_table(r):
    fan = [16, 16, 16]
    tbl = tp.hierarchical_tree_table(fan, oversubscription=r)
    fit_tbl = tp.fit_rent_points(tbl)
    assert fit_tbl.p == pytest.approx(tp.tapered_exponent(16, r), abs=1e-9)
    G = tp.hierarchical_tree([4, 4, 4], oversubscription=r)
    pts = tp.rent_points(G, tp.hierarchical_tree_modules(G))
    tbl_small = tp.hierarchical_tree_table([4, 4, 4], oversubscription=r)
    for _, row in tbl_small.iterrows():
        got = pts[pts.level == row.level]
        assert set(got.gates) == {row.gates}
        assert set(got.links) == {row.links}
    assert tp.fit_rent_points(pts).p == pytest.approx(tp.tapered_exponent(4, r), abs=1e-9)


def test_hierarchical_tree_explicit_uplinks_and_wan():
    G = tp.hierarchical_tree([8, 4], uplinks=[4, 8])
    assert "wan" in G
    top = [n for n, d in G.nodes(data=True) if d.get("level") == 2]
    assert len(top) == 1
    assert G.edges[top[0], "wan"]["links"] == 8


@pytest.mark.parametrize("d", [2, 3])
def test_mesh_exponent_analytic_and_graph(d):
    sides = [2, 3, 4]
    tbl = tp.mesh_rent_points_analytic(d, sides + [8, 16])
    assert tp.fit_rent_points(tbl).p == pytest.approx(tp.mesh_exponent(d), abs=1e-9)
    n = 7
    G = tp.mesh(d, n)
    pts = tp.rent_points(G, tp.mesh_modules(d, n, sides))
    for s, (_, row) in zip(sides, pts.iterrows(), strict=True):
        assert row.gates == s**d
        assert row.links == 2 * d * s ** (d - 1)


def test_recursive_bisection_recovers_half_for_grid():
    G = tp.mesh(2, 16)
    pts = tp.recursive_bisection_points(G, min_nodes=4, seed=0)
    assert pts.iloc[0].links == 0 and pts.iloc[0].gates == 256
    fit = tp.fit_rent_points(pts)
    assert abs(fit.p - 0.5) < 0.15
    assert pts.depth.max() >= 5


def test_traffic_matrix_graph_and_bisection():
    # two tight cliques with a thin bridge: the workload is local
    n = 8
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j and (i < 4) == (j < 4):
                M[i, j] = 100.0
    M[0, 4] = M[4, 0] = 1.0
    G = tp.graph_from_traffic_matrix(M, gates=[1e9] * n)
    assert G.number_of_nodes() == n
    assert G.edges[0, 4]["capacity"] == 2.0
    pts = tp.recursive_bisection_points(G, weight="capacity", min_nodes=2)
    halves = pts[pts.depth == 1]
    assert (halves.capacity == 2.0).all()  # KL found the bridge cut
    assert halves.gates.iloc[0] == 4e9
