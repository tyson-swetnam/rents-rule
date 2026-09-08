"""Synthetic topologies with known Rent exponents, and tools to extract (G, T) points from
any graph.

Conventions: node attribute ``gates`` (transistors or abstract gate count; switches carry
0); edge attributes ``links`` (physical links the edge stands for) and ``capacity``
(aggregate capacity, e.g. Gb/s). All generators set all three. ``cut_terminals`` counts
edges with exactly one endpoint inside a module, which is the Rent terminal count.
"""
from __future__ import annotations

import itertools
import math
from typing import Iterable, Sequence

import networkx as nx
import numpy as np
import pandas as pd

from .rent import RentFit, fit_rent

GATES = "gates"
LINKS = "links"
CAPACITY = "capacity"


# ----------------------------------------------------------------------------- measuring
def cut_terminals(
    G: nx.Graph, nodes: Iterable, links_attr: str = LINKS, capacity_attr: str = CAPACITY
) -> tuple[int, float]:
    """Number of links and total capacity crossing the boundary of ``nodes``."""
    module = set(nodes)
    n_links = 0
    cap = 0.0
    multi = G.is_multigraph()
    for u in module:
        for v, data in G.adj[u].items():
            if v in module:
                continue
            if multi:
                for d in data.values():
                    n_links += int(d.get(links_attr, 1))
                    cap += float(d.get(capacity_attr, 1.0))
            else:
                n_links += int(data.get(links_attr, 1))
                cap += float(data.get(capacity_attr, 1.0))
    return n_links, cap


def module_gates(G: nx.Graph, nodes: Iterable, attr: str = GATES) -> float:
    return float(sum(G.nodes[n].get(attr, 0.0) for n in nodes))


def rent_points(G: nx.Graph, modules: Sequence[dict]) -> pd.DataFrame:
    """(G, T) rows for a list of modules ``{"level", "level_index", "name", "nodes"}``."""
    rows = []
    for m in modules:
        links, cap = cut_terminals(G, m["nodes"])
        rows.append(
            {
                "level": m.get("level"),
                "level_index": m.get("level_index"),
                "name": m.get("name"),
                "gates": module_gates(G, m["nodes"]),
                "links": links,
                "capacity": cap,
                "n_nodes": len(m["nodes"]),
            }
        )
    return pd.DataFrame(rows)


def fit_rent_points(
    df: pd.DataFrame, g_col: str = "gates", t_col: str = "links", **kwargs
) -> RentFit:
    """Fit Rent's rule to a points table, ignoring modules with zero gates or terminals
    (e.g. the root of a tree, which has no external links)."""
    sub = df[(df[g_col] > 0) & (df[t_col] > 0)]
    return fit_rent(sub[g_col].to_numpy(), sub[t_col].to_numpy(), **kwargs)


# ----------------------------------------------------------------------------- fat-tree
def fat_tree(k: int, gates_per_host: float = 1.0, link_capacity: float = 1.0) -> nx.Graph:
    """Al-Fares k-ary fat-tree: k pods, k/2 edge + k/2 aggregation switches per pod,
    (k/2)^2 core switches, k^3/4 hosts, full bisection bandwidth (Rent p = 1)."""
    if k < 2 or k % 2:
        raise ValueError("k must be an even integer >= 2")
    half = k // 2
    G = nx.Graph(k=k)
    for j in range(half * half):
        G.add_node(f"core{j}", kind="core", pod=None, gates=0.0)
    for pod in range(k):
        for a in range(half):
            agg = f"p{pod}a{a}"
            G.add_node(agg, kind="agg", pod=pod, gates=0.0)
            for c in range(half):
                G.add_edge(agg, f"core{a * half + c}", links=1, capacity=link_capacity)
        for e in range(half):
            edge = f"p{pod}e{e}"
            G.add_node(edge, kind="edge", pod=pod, edge=e, gates=0.0)
            for a in range(half):
                G.add_edge(edge, f"p{pod}a{a}", links=1, capacity=link_capacity)
            for h in range(half):
                host = f"p{pod}e{e}h{h}"
                G.add_node(host, kind="host", pod=pod, edge=e, gates=gates_per_host)
                G.add_edge(host, edge, links=1, capacity=link_capacity)
    return G


def fat_tree_modules(G: nx.Graph) -> list[dict]:
    """Natural modules of a fat-tree: each host; each edge switch with its hosts; each pod;
    the whole tree (which has no external links and is dropped by ``fit_rent_points``)."""
    mods = []
    for n, d in G.nodes(data=True):
        if d.get("kind") == "host":
            mods.append(dict(level="host", level_index=0, name=n, nodes={n}))
    for n, d in G.nodes(data=True):
        if d.get("kind") == "edge":
            nodes = {n} | {v for v in G.adj[n] if G.nodes[v].get("kind") == "host"}
            mods.append(dict(level="edge", level_index=1, name=n, nodes=nodes))
    pods = sorted({d["pod"] for _, d in G.nodes(data=True) if d.get("pod") is not None})
    for p in pods:
        nodes = {n for n, d in G.nodes(data=True) if d.get("pod") == p}
        mods.append(dict(level="pod", level_index=2, name=f"pod{p}", nodes=nodes))
    mods.append(dict(level="tree", level_index=3, name="tree", nodes=set(G.nodes)))
    return mods


# ----------------------------------------------------------------------------- generic tree
def _uplinks_from_oversubscription(fanouts: Sequence[int], oversubscription) -> list[int]:
    L = len(fanouts)
    if np.isscalar(oversubscription):
        r = [float(oversubscription)] * L
    else:
        r = [float(v) for v in oversubscription]
        if len(r) != L:
            raise ValueError("oversubscription must be a scalar or one value per level")
    ups: list[int] = []
    for level in range(L):
        down = fanouts[0] if level == 0 else fanouts[level] * ups[level - 1]
        ups.append(max(1, int(round(down / r[level]))))
    return ups


def hierarchical_tree(
    fanouts: Sequence[int],
    oversubscription=1.0,
    uplinks: Sequence[int] | None = None,
    gates_per_host: float = 1.0,
    link_capacity: float = 1.0,
) -> nx.Graph:
    """A multi-level switch tree. ``fanouts[l]`` children per level-l switch (level 0
    switches attach hosts). Uplinks per switch are ``uplinks[l]`` if given, else derived
    from the per-level oversubscription ``r``: ``up[l] = down[l] / r[l]``. Top-level
    uplinks go to a ``wan`` node. Parallel uplinks are one edge with ``links = up[l]``."""
    fanouts = [int(f) for f in fanouts]
    if not fanouts or min(fanouts) < 1:
        raise ValueError("fanouts must be a non-empty list of positive integers")
    L = len(fanouts)
    ups = [int(u) for u in uplinks] if uplinks is not None else _uplinks_from_oversubscription(
        fanouts, oversubscription
    )
    if len(ups) != L:
        raise ValueError("uplinks must have one entry per level")
    G = nx.Graph(fanouts=fanouts, uplinks=ups)
    G.add_node("wan", kind="wan", level=L + 1, gates=0.0)
    counts = [int(np.prod(fanouts[level + 1 :])) for level in range(L)]
    for level in range(L - 1, -1, -1):
        for j in range(counts[level]):
            s = f"s{level}_{j}"
            G.add_node(s, kind="switch", level=level + 1, gates=0.0)
            parent = "wan" if level == L - 1 else f"s{level + 1}_{j // fanouts[level + 1]}"
            G.add_edge(s, parent, links=ups[level], capacity=ups[level] * link_capacity)
    n_hosts = int(np.prod(fanouts))
    for i in range(n_hosts):
        h = f"h{i}"
        G.add_node(h, kind="host", level=0, gates=gates_per_host)
        G.add_edge(h, f"s0_{i // fanouts[0]}", links=1, capacity=link_capacity)
    return G


def _subtree(G: nx.Graph, root) -> set:
    seen = {root}
    stack = [root]
    while stack:
        u = stack.pop()
        for v in G.adj[u]:
            if v not in seen and G.nodes[v]["level"] < G.nodes[u]["level"]:
                seen.add(v)
                stack.append(v)
    return seen


def hierarchical_tree_modules(G: nx.Graph) -> list[dict]:
    mods = []
    for n, d in G.nodes(data=True):
        if d.get("kind") == "host":
            mods.append(dict(level="host", level_index=0, name=n, nodes={n}))
    for n, d in G.nodes(data=True):
        if d.get("kind") == "switch":
            mods.append(
                dict(level=f"L{d['level']}", level_index=d["level"], name=n, nodes=_subtree(G, n))
            )
    return mods


def hierarchical_tree_table(
    fanouts: Sequence[int],
    oversubscription=1.0,
    uplinks: Sequence[int] | None = None,
    gates_per_host: float = 1.0,
) -> pd.DataFrame:
    """Analytic (G, T) per level for :func:`hierarchical_tree` without building the graph."""
    fanouts = [int(f) for f in fanouts]
    ups = [int(u) for u in uplinks] if uplinks is not None else _uplinks_from_oversubscription(
        fanouts, oversubscription
    )
    rows = [dict(level="host", level_index=0, gates=gates_per_host, links=1)]
    for level in range(len(fanouts)):
        rows.append(
            dict(
                level=f"L{level + 1}",
                level_index=level + 1,
                gates=gates_per_host * int(np.prod(fanouts[: level + 1])),
                links=ups[level],
            )
        )
    return pd.DataFrame(rows)


def tapered_exponent(k: float, r: float) -> float:
    """Rent exponent of a uniform tree with radix ``k`` and per-level oversubscription
    ``r``: ``p = 1 - ln r / ln k`` (``r = 1`` gives 1; ``r = k`` gives 0)."""
    if k <= 1:
        raise ValueError("k must exceed 1")
    if r <= 0:
        raise ValueError("r must be positive")
    return 1.0 - math.log(r) / math.log(k)


# ----------------------------------------------------------------------------- meshes
def mesh(d: int, n: int, gates_per_node: float = 1.0, link_capacity: float = 1.0) -> nx.Graph:
    """``d``-dimensional grid with ``n`` nodes per side (Rent p = 1 - 1/d)."""
    if d < 1 or n < 2:
        raise ValueError("need d >= 1 and n >= 2")
    G = nx.grid_graph(dim=[n] * d)
    nx.set_node_attributes(G, gates_per_node, GATES)
    nx.set_node_attributes(G, "host", "kind")
    nx.set_edge_attributes(G, 1, LINKS)
    nx.set_edge_attributes(G, link_capacity, CAPACITY)
    return G


def mesh_modules(d: int, n: int, sides: Sequence[int]) -> list[dict]:
    """Interior sub-cubes of side ``s`` (anchored one node in from the corner, so every
    face has neighbours): ``G = s^d`` gates, ``T = 2 d s^(d-1)`` links."""
    mods = []
    for s in sides:
        if s < 1 or s > n - 2:
            raise ValueError(f"side {s} must be in [1, n-2] for an interior module")
        nodes = set(itertools.product(range(1, 1 + s), repeat=d))
        if d == 1:
            nodes = {t[0] for t in nodes}
        mods.append(dict(level=f"cube{s}", level_index=s, name=f"cube{s}", nodes=nodes))
    return mods


def mesh_rent_points_analytic(d: int, sides: Sequence[int]) -> pd.DataFrame:
    return pd.DataFrame(
        [dict(level=f"cube{s}", gates=float(s**d), links=2 * d * s ** (d - 1)) for s in sides]
    )


def mesh_exponent(d: int) -> float:
    return 1.0 - 1.0 / d


# ----------------------------------------------------------------------------- bisection
def recursive_bisection_points(
    G: nx.Graph,
    weight: str | None = CAPACITY,
    min_nodes: int = 4,
    max_depth: int | None = None,
    seed: int = 0,
    gates_attr: str = GATES,
) -> pd.DataFrame:
    """Landman-Russo style measurement: recursively bisect ``G`` (Kernighan-Lin, weighted
    by ``weight``) and record (gates, links, capacity) of every block against the full
    graph. Works on a weighted traffic graph too (see :func:`graph_from_traffic_matrix`),
    which yields the *workload* Rent exponent."""
    from networkx.algorithms.community import kernighan_lin_bisection

    rows = []
    stack = [(frozenset(G.nodes), 0)]
    while stack:
        nodes, depth = stack.pop()
        links, cap = cut_terminals(G, nodes)
        rows.append(
            dict(
                depth=depth,
                n_nodes=len(nodes),
                gates=module_gates(G, nodes, gates_attr),
                links=links,
                capacity=cap,
            )
        )
        if len(nodes) < 2 * min_nodes or (max_depth is not None and depth >= max_depth):
            continue
        sub = G.subgraph(nodes)
        a, b = kernighan_lin_bisection(sub, weight=weight, seed=seed + depth)
        if not a or not b:
            continue
        stack.append((frozenset(a), depth + 1))
        stack.append((frozenset(b), depth + 1))
    return pd.DataFrame(rows)


def graph_from_traffic_matrix(M, labels=None, gates=None) -> nx.Graph:
    """Undirected weighted graph from a traffic matrix (bytes from i to j). Edge
    ``capacity`` = ``weight`` = bytes in both directions; node ``gates`` from ``gates``."""
    M = np.asarray(M, dtype=float)
    if M.ndim != 2 or M.shape[0] != M.shape[1]:
        raise ValueError("traffic matrix must be square")
    n = M.shape[0]
    labels = list(labels) if labels is not None else list(range(n))
    gates = list(gates) if gates is not None else [1.0] * n
    G = nx.Graph()
    for i in range(n):
        G.add_node(labels[i], kind="host", gates=float(gates[i]))
    for i in range(n):
        for j in range(i + 1, n):
            w = M[i, j] + M[j, i]
            if w > 0:
                G.add_edge(labels[i], labels[j], links=1, capacity=float(w), weight=float(w))
    return G
