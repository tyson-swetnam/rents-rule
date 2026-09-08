"""Parse InfiniBand fabric discovery (``ibnetdiscover``) and Slurm topology
(``scontrol show topology``) into graphs; derive leaf-level Rent points."""
from __future__ import annotations

import re
from typing import Callable

import networkx as nx
import pandas as pd

IB_RATE_GBPS_PER_LANE = {
    "SDR": 2.5, "DDR": 5.0, "QDR": 10.0, "FDR10": 10.3125, "FDR": 14.0625,
    "EDR": 25.0, "HDR": 50.0, "NDR": 100.0, "XDR": 200.0,
}

_NODE_RE = re.compile(r'^(Switch|Ca|Rt)\s+(\d+)\s+"([^"]+)"\s*#\s*"([^"]*)"(.*)$')
_LINK_RE = re.compile(
    r'^\[(\d+)\](?:\([0-9a-fA-F]+\))?\s+"([^"]+)"\[(\d+)\](?:\([0-9a-fA-F]+\))?\s*(?:#(.*))?$'
)
_RATE_RE = re.compile(r"(\d+)x([A-Z]+\d*)")
_KIND = {"Switch": "switch", "Ca": "ca", "Rt": "router"}


def parse_ibnetdiscover(text: str) -> nx.MultiGraph:
    """Fabric graph: nodes are GUID strings (``S-...`` switches, ``H-...`` HCAs) with
    ``kind``, ``desc``, ``ports``, ``lid``; each physical link is one edge keyed by its
    port pair with ``links=1``, ``lanes``, ``speed`` and ``capacity`` (Gb/s per direction)."""
    G = nx.MultiGraph()
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m = _NODE_RE.match(line)
        if m:
            kind, nports, guid, desc, rest = m.groups()
            cur = guid
            lid = re.search(r"\blid (\d+)", rest)
            G.add_node(guid, kind=_KIND[kind], ports=int(nports), desc=desc, lid=int(lid.group(1)) if lid else None)
            continue
        m = _LINK_RE.match(line)
        if m and cur is not None:
            lport, rguid, rport, comment = m.groups()
            lport, rport = int(lport), int(rport)
            rm = _RATE_RE.search(comment or "")
            width = int(rm.group(1)) if rm else 4
            speed = rm.group(2) if rm else None
            if rguid not in G:
                G.add_node(rguid, kind="unknown", ports=None, desc="", lid=None)
            key = tuple(sorted([(cur, lport), (rguid, rport)]))
            if not G.has_edge(cur, rguid, key=key):
                per_lane = IB_RATE_GBPS_PER_LANE.get(speed) if speed else None
                cap = width * per_lane if per_lane else float("nan")
                G.add_edge(cur, rguid, key=key, links=1, lanes=width, speed=speed, capacity=cap)
    for n, d in G.nodes(data=True):
        if d.get("kind") == "unknown":
            d["kind"] = "ca" if n.startswith("H-") else ("switch" if n.startswith("S-") else "unknown")
    return G


def classify_switches(G: nx.MultiGraph) -> dict[str, str]:
    """``leaf`` if the switch has any HCA neighbour, else ``spine``."""
    out = {}
    for n, d in G.nodes(data=True):
        if d.get("kind") != "switch":
            continue
        has_ca = any(G.nodes[v].get("kind") == "ca" for v in G.adj[n])
        out[n] = "leaf" if has_ca else "spine"
    return out


def fabric_summary(G: nx.MultiGraph) -> dict:
    kinds = classify_switches(G)
    speeds: dict[str, int] = {}
    for _, _, d in G.edges(data=True):
        s = f"{d.get('lanes')}x{d.get('speed')}"
        speeds[s] = speeds.get(s, 0) + 1
    return {
        "switches": sum(1 for _, d in G.nodes(data=True) if d.get("kind") == "switch"),
        "leaf_switches": sum(1 for v in kinds.values() if v == "leaf"),
        "spine_switches": sum(1 for v in kinds.values() if v == "spine"),
        "hcas": sum(1 for _, d in G.nodes(data=True) if d.get("kind") == "ca"),
        "links": G.number_of_edges(),
        "link_rates": speeds,
    }


def leaf_modules(G: nx.MultiGraph, gates_for_host: Callable[[str], float] | None = None) -> pd.DataFrame:
    """One row per leaf switch: the module is the switch plus its attached HCAs.
    ``gates`` = sum over HCAs of ``gates_for_host(desc)`` (default 1 per HCA);
    ``links``/``lanes``/``gbps`` count the uplinks leaving the module. Hosts with HCAs on
    several leaves (multi-rail) appear in each leaf's module."""
    rows = []
    for s, d in G.nodes(data=True):
        if d.get("kind") != "switch":
            continue
        cas = [v for v in G.adj[s] if G.nodes[v].get("kind") == "ca"]
        if not cas:
            continue
        module = set(cas) | {s}
        up_links = up_lanes = down_links = 0
        up_gbps = down_gbps = 0.0
        for v, edict in G.adj[s].items():
            for e in edict.values():
                cap = e.get("capacity") or 0.0
                if v in module:
                    down_links += 1
                    down_gbps += cap
                else:
                    up_links += 1
                    up_lanes += int(e.get("lanes", 4))
                    up_gbps += cap
        gates = sum((gates_for_host(G.nodes[c].get("desc", "")) if gates_for_host else 1.0) for c in cas)
        rows.append(
            {
                "leaf": d.get("desc") or s,
                "guid": s,
                "n_hosts": len(cas),
                "gates": float(gates),
                "links": up_links,
                "lanes": up_lanes,
                "gbps": up_gbps,
                "downlinks": down_links,
                "down_gbps": down_gbps,
                "oversubscription": (down_gbps / up_gbps) if up_gbps else float("nan"),
            }
        )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- slurm topology
def _split_outside_brackets(s: str) -> list[str]:
    out, depth, cur = [], 0, []
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return [p for p in out if p]


def expand_hostlist(s: str) -> list[str]:
    """Expand Slurm hostlist syntax: ``node[01-04,07],gpu[1-2]`` -> individual names."""
    out: list[str] = []
    for part in _split_outside_brackets(s.strip()):
        m = re.match(r"^(.*?)\[([^\]]+)\](.*)$", part)
        if not m:
            out.append(part)
            continue
        prefix, body, suffix = m.groups()
        for rng in body.split(","):
            rng = rng.strip()
            if "-" in rng:
                a, b = rng.split("-", 1)
                width = len(a)
                for i in range(int(a), int(b) + 1):
                    out.extend(expand_hostlist(f"{prefix}{str(i).zfill(width)}{suffix}"))
            else:
                out.extend(expand_hostlist(f"{prefix}{rng}{suffix}"))
    return out


def parse_slurm_topology(text: str) -> nx.DiGraph:
    """``scontrol show topology`` -> directed tree (switch -> child switch / node)."""
    G = nx.DiGraph()
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("SwitchName="):
            continue
        fields = dict(kv.split("=", 1) for kv in s.split() if "=" in kv)
        name = fields["SwitchName"]
        G.add_node(name, kind="switch", level=int(fields.get("Level", 0)), link_speed=fields.get("LinkSpeed"))
        for child in expand_hostlist(fields.get("Switches", "")):
            G.add_node(child, kind="switch")
            G.add_edge(name, child)
        for node in expand_hostlist(fields.get("Nodes", "")):
            G.add_node(node, kind="node", level=-1)
            G.add_edge(name, node)
    return G


def slurm_topology_table(G: nx.DiGraph) -> pd.DataFrame:
    """Hosts under each switch (the grouping needed for the census when link rates
    are known from elsewhere)."""
    rows = []
    for n, d in G.nodes(data=True):
        if d.get("kind") != "switch":
            continue
        hosts = [v for v in nx.descendants(G, n) if G.nodes[v].get("kind") == "node"]
        rows.append({"switch": n, "level": d.get("level"), "n_hosts": len(hosts), "hosts": sorted(hosts)})
    return pd.DataFrame(rows).sort_values(["level", "switch"]).reset_index(drop=True) if rows else pd.DataFrame(rows)
