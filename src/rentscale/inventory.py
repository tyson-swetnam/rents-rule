"""Parse node inventories written by ``hardware/inventory/inventory_node.sh`` and resolve
a hierarchy YAML into a Rent census (gates and terminals per module)."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .rent import RentFit, fit_rent, locality_steps

PKG_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = PKG_ROOT / "hardware" / "reference"
TRANSISTOR_TABLE = REF_DIR / "transistor_counts.csv"
LINK_TABLE = REF_DIR / "link_bandwidths.csv"

#: lanes per Ethernet port by speed (Mb/s); approximate (100G may be 2 or 4 lanes)
ETH_LANES_BY_MBPS = {
    1000: 4, 10000: 1, 25000: 1, 40000: 4, 50000: 2, 100000: 4, 200000: 4, 400000: 8, 800000: 8,
}
#: NVLink generation per GPU part key (link key in link_bandwidths.csv)
NVLINK_BY_PART = {
    "nvidia-v100": "nvlink2_link",
    "nvidia-a100": "nvlink3_link",
    "nvidia-a30": "nvlink3_link",
    "nvidia-h100": "nvlink4_link",
    "nvidia-b200": "nvlink5_link",
}
PCIE_GBPS_PER_LANE = {1: 2.0, 2: 4.0, 3: 7.877, 4: 15.754, 5: 31.508, 6: 63.0}


# ----------------------------------------------------------------------------- tables
def load_transistor_table(path: Path | str | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or TRANSISTOR_TABLE)
    df["aliases"] = df["aliases"].fillna("").astype(str)
    return df


def load_link_table(path: Path | str | None = None) -> pd.DataFrame:
    return pd.read_csv(path or LINK_TABLE)


def match_part(name, table: pd.DataFrame):
    """Match a device name (``'NVIDIA A100-SXM4-80GB'``, ``'AMD EPYC 7763 64-Core
    Processor'``) or a table key to a row, by exact key or longest alias substring.
    Returns the row (``pd.Series``) or ``None``."""
    if name is None:
        return None
    key = str(name).strip().lower()
    exact = table[table["key"].str.lower() == key]
    if len(exact):
        return exact.iloc[0]
    norm = _normalize_name(key)
    best, best_len = None, 0
    for _, row in table.iterrows():
        for alias in str(row["aliases"]).split("|"):
            a = _normalize_name(alias)
            if a and a in norm and len(a) > best_len:
                best, best_len = row, len(a)
    return best


_DECORATIONS = re.compile(r"\((?:r|tm|c)\)|\bcpu\b|@.*$", re.IGNORECASE)


def _normalize_name(s: str) -> str:
    """Lower-case, drop (R)/(TM) marks, 'CPU', and clock suffixes, collapse whitespace."""
    s = _DECORATIONS.sub(" ", str(s).lower())
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------------------- parsers
_UNIT_VAL = re.compile(r"^(-?\d+(?:\.\d+)?)\s*(MiB|GiB|W|%|MHz|Gb/s)?$")


def parse_nvidia_smi_query_csv(text: str) -> list[dict]:
    """``nvidia-smi --query-gpu=... --format=csv``: header units stripped, numbers parsed."""
    rows = list(csv.reader(io.StringIO(text.strip())))
    if not rows:
        return []
    header = [re.sub(r"\s*\[.*?\]\s*$", "", h.strip()) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if len(r) != len(header):
            continue
        d = {}
        for h, v in zip(header, r, strict=True):
            v = v.strip()
            m = _UNIT_VAL.match(v)
            d[h] = float(m.group(1)) if m else v
        out.append(d)
    return out


def parse_lscpu_json(text: str) -> dict:
    data = json.loads(text)
    return {e["field"].rstrip(":").strip(): e["data"] for e in data.get("lscpu", []) if "field" in e}


def parse_lscpu_text(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def parse_ibstat(text: str) -> list[dict]:
    """``ibstat``: one dict per port with ca, port, state, physical_state, rate_gbps, link_layer."""
    ports: list[dict] = []
    ca = None
    cur = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^CA '([^']+)'", s)
        if m:
            ca = m.group(1)
            cur = None
            continue
        m = re.match(r"^Port (\d+):", s)
        if m:
            cur = {"ca": ca, "port": int(m.group(1))}
            ports.append(cur)
            continue
        if cur is not None and ":" in s:
            k, v = s.split(":", 1)
            k = k.strip().lower().replace(" ", "_")
            v = v.strip()
            if k == "rate":
                try:
                    cur["rate_gbps"] = float(v.split()[0])
                except (ValueError, IndexError):
                    cur["rate_gbps"] = np.nan
            elif k in ("state", "physical_state", "link_layer"):
                cur[k] = v
    return ports


def parse_ib_sysfs(text: str) -> dict[tuple[str, int], dict]:
    """``ib_sysfs.txt`` written by inventory_node.sh: blocks of ``device=.. port=..`` then
    ``state=``, ``phys_state=``, ``rate=200 Gb/sec (4X HDR)``, ``link_layer=``."""
    out: dict[tuple[str, int], dict] = {}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^device=(\S+)\s+port=(\d+)", s)
        if m:
            cur = {"device": m.group(1), "port": int(m.group(2))}
            out[(m.group(1), int(m.group(2)))] = cur
            continue
        if cur is not None and "=" in s:
            k, v = s.split("=", 1)
            cur[k] = v
            if k == "rate":
                w = re.search(r"(\d+)X", v)
                cur["width"] = int(w.group(1)) if w else None
                g = re.match(r"([\d.]+)", v)
                cur["rate_gbps"] = float(g.group(1)) if g else np.nan
    return out


def parse_ethtool_link(text: str) -> dict:
    d: dict = {}
    m = re.search(r"Speed:\s*(\d+)Mb/s", text)
    d["speed_mbps"] = int(m.group(1)) if m else None
    m = re.search(r"Link detected:\s*(yes|no)", text)
    d["link"] = (m.group(1) == "yes") if m else None
    m = re.search(r"Port:\s*(.+)", text)
    d["port_type"] = m.group(1).strip() if m else None
    return d


def parse_nvidia_smi_topo(text: str) -> dict[str, dict[str, str]]:
    """``nvidia-smi topo -m`` matrix -> ``{'GPU0': {'GPU1': 'NV12', 'mlx5_0': 'PXB', ...}}``."""
    header = None
    matrix: dict[str, dict[str, str]] = {}
    for line in text.splitlines():
        toks = [t.strip() for t in (line.split("\t") if "\t" in line else line.split()) if t.strip()]
        if not toks:
            continue
        if header is None:
            if toks[0].startswith("GPU0"):
                header = toks
            continue
        if re.match(r"^GPU\d+$", toks[0]):
            matrix[toks[0]] = dict(zip(header, toks[1:], strict=False))
    return matrix


def nvlink_counts_from_topo(matrix: dict[str, dict[str, str]]) -> dict[str, int]:
    """Number of NVLink links per GPU from the topology matrix (sum of ``NV<n>`` entries)."""
    out = {}
    for g, row in matrix.items():
        n = 0
        for h, v in row.items():
            m = re.match(r"^NV(\d+)$", v)
            if m and h.startswith("GPU"):
                n += int(m.group(1))
        out[g] = n
    return out


# ----------------------------------------------------------------------------- node summary
def _read(path: Path) -> str | None:
    if path.exists() and path.stat().st_size > 0:
        return path.read_text(errors="replace")
    return None


def node_summary(node_dir: Path | str, transistor_table=None, link_table=None) -> dict:
    """Per-node gates and terminals from an ``inventory_node.sh`` output directory.
    Unknown parts are listed, never guessed."""
    node_dir = Path(node_dir)
    tt = transistor_table if transistor_table is not None else load_transistor_table()
    lt = link_table if link_table is not None else load_link_table()
    lt_by_key = {r["key"]: r for _, r in lt.iterrows()}
    out: dict = {
        "host": node_dir.name,
        "gpus": [],
        "cpu": {},
        "ib_ports": [],
        "eth_ports": [],
        "unknown_parts": [],
        "missing": [],
    }
    gates = 0.0

    # GPUs
    text = _read(node_dir / "nvidia-smi_query.csv")
    if text:
        for g in parse_nvidia_smi_query_csv(text):
            name = g.get("name")
            row = match_part(name, tt)
            entry = {
                "index": g.get("index"),
                "name": name,
                "pcie_gen": g.get("pcie.link.gen.max"),
                "pcie_width": g.get("pcie.link.width.max"),
                "transistors": None,
                "part_key": None,
                "nvlinks": None,
            }
            if row is not None and pd.notna(row["transistors_billion"]):
                entry["transistors"] = float(row["transistors_billion"]) * 1e9
                entry["part_key"] = row["key"]
                gates += entry["transistors"]
            else:
                out["unknown_parts"].append(str(name))
            out["gpus"].append(entry)
    else:
        out["missing"].append("nvidia-smi_query.csv")

    text = _read(node_dir / "nvidia-smi_topo.txt")
    if text:
        counts = nvlink_counts_from_topo(parse_nvidia_smi_topo(text))
        for e in out["gpus"]:
            if e.get("index") is not None:
                e["nvlinks"] = counts.get(f"GPU{int(e['index'])}")

    # die-level terminals per GPU (NVLink + PCIe), where the generation is known
    for e in out["gpus"]:
        lanes = 0.0
        gbps = 0.0
        nv_key = NVLINK_BY_PART.get(e.get("part_key") or "")
        if nv_key and e.get("nvlinks") and nv_key in lt_by_key:
            r = lt_by_key[nv_key]
            lanes += e["nvlinks"] * float(r["lanes_per_direction"])
            gbps += e["nvlinks"] * float(r["gbps_per_direction"])
        gen, width = e.get("pcie_gen"), e.get("pcie_width")
        if gen and width:
            lanes += float(width)
            gbps += float(width) * PCIE_GBPS_PER_LANE.get(int(gen), np.nan)
        e["terminals"] = {"lanes": lanes, "gbps": gbps}

    # CPU
    text = _read(node_dir / "lscpu.json")
    info = parse_lscpu_json(text) if text else {}
    if not info:
        text = _read(node_dir / "lscpu.txt")
        info = parse_lscpu_text(text) if text else {}
    if info:
        model = info.get("Model name")

        def _int(v, default=1):
            try:
                return int(str(v).split()[0])
            except (ValueError, IndexError, AttributeError):
                return default

        sockets = _int(info.get("Socket(s)"))
        out["cpu"] = {
            "model": model,
            "sockets": sockets,
            "cores_per_socket": _int(info.get("Core(s) per socket"), 0),
            "threads_per_core": _int(info.get("Thread(s) per core"), 1),
            "transistors": None,
            "part_key": None,
        }
        row = match_part(model, tt)
        if row is not None and pd.notna(row["transistors_billion"]):
            out["cpu"]["transistors"] = float(row["transistors_billion"]) * 1e9 * sockets
            out["cpu"]["part_key"] = row["key"]
            gates += out["cpu"]["transistors"]
        else:
            out["unknown_parts"].append(str(model))
    else:
        out["missing"].append("lscpu.json")

    # InfiniBand ports (Ethernet-link-layer HCAs are counted through ethtool instead)
    text = _read(node_dir / "ib_sysfs.txt")
    widths = parse_ib_sysfs(text) if text else {}
    text = _read(node_dir / "ibstat.txt")
    if text:
        for p in parse_ibstat(text):
            if p.get("state") != "Active":
                continue
            if str(p.get("link_layer", "InfiniBand")).lower() == "ethernet":
                continue
            w = widths.get((p["ca"], p["port"]), {}).get("width")
            p["lanes"] = int(w) if w else 4
            out["ib_ports"].append(p)
    else:
        out["missing"].append("ibstat.txt")

    # Ethernet ports
    for f in sorted(node_dir.glob("ethtool_*.txt")):
        if f.name.startswith("ethtool_i_"):
            continue
        iface = f.name[len("ethtool_") : -4]
        d = parse_ethtool_link(f.read_text(errors="replace"))
        if d.get("link") and d.get("speed_mbps"):
            out["eth_ports"].append(
                {
                    "iface": iface,
                    "speed_mbps": d["speed_mbps"],
                    "lanes": ETH_LANES_BY_MBPS.get(d["speed_mbps"], 1),
                    "port_type": d.get("port_type"),
                }
            )

    ib_lanes = sum(p["lanes"] for p in out["ib_ports"])
    ib_gbps = float(np.nansum([p.get("rate_gbps", np.nan) for p in out["ib_ports"]])) if out["ib_ports"] else 0.0
    eth_lanes = sum(p["lanes"] for p in out["eth_ports"])
    eth_gbps = sum(p["speed_mbps"] / 1000.0 for p in out["eth_ports"])
    out["gates"] = gates
    out["terminals"] = {
        "lanes": ib_lanes + eth_lanes,
        "ports": len(out["ib_ports"]) + len(out["eth_ports"]),
        "gbps": ib_gbps + eth_gbps,
    }
    return out


# ----------------------------------------------------------------------------- census
def load_hierarchy(path: Path | str) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def census(hierarchy: dict, transistor_table=None, link_table=None, group: str | None = None) -> pd.DataFrame:
    """Resolve a hierarchy dict into one row per module: level, gates, lanes, ports, gbps,
    plus the parts and links that could not be resolved."""
    tt = transistor_table if transistor_table is not None else load_transistor_table()
    lt = link_table if link_table is not None else load_link_table()
    lt_by_key = {r["key"]: r for _, r in lt.iterrows()}
    levels = list(hierarchy.get("levels", []))
    mods = {m["name"]: m for m in hierarchy.get("modules", [])}
    cache: dict[str, float] = {}
    unknown: dict[str, list[str]] = {}

    def gates_of(name: str, stack: tuple = ()) -> float:
        if name in cache:
            return cache[name]
        if name in stack:
            raise ValueError(f"cycle in hierarchy at {name}")
        if name not in mods:
            raise KeyError(f"module {name!r} referenced but not defined")
        m = mods[name]
        g = 0.0
        if m.get("gates_override") is not None:
            g = float(m["gates_override"])
        else:
            for p in m.get("parts") or []:
                q = float(p.get("qty", 1))
                if q == 0:
                    continue
                row = match_part(p["part"], tt)
                if row is None or pd.isna(row["transistors_billion"]):
                    unknown.setdefault(name, []).append(str(p["part"]))
                else:
                    g += q * float(row["transistors_billion"]) * 1e9
            for c in m.get("children") or []:
                g += float(c.get("qty", 1)) * gates_of(c["module"], stack + (name,))
        cache[name] = g
        return g

    rows = []
    for m in hierarchy.get("modules", []):
        if group is not None and m.get("group") != group:
            continue
        lanes = ports = gbps = 0.0
        unknown_links = []
        for link in m.get("external_links") or []:
            q = float(link.get("qty", 1))
            r = lt_by_key.get(link["link"])
            if r is None:
                unknown_links.append(str(link["link"]))
                continue
            lanes += q * float(r["lanes_per_direction"])
            ports += q
            gbps += q * float(r["gbps_per_direction"])
        rows.append(
            {
                "group": m.get("group", ""),
                "level": m["level"],
                "level_index": levels.index(m["level"]) if m["level"] in levels else -1,
                "module": m["name"],
                "gates": gates_of(m["name"]),
                "lanes": lanes,
                "ports": ports,
                "gbps": gbps,
                "unknown_parts": ";".join(unknown.get(m["name"], [])),
                "unknown_links": ";".join(unknown_links),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["group", "level_index", "module"]).reset_index(drop=True)
    return df


def census_report(df: pd.DataFrame, t_cols=("lanes", "ports", "gbps"), bootstrap: int = 200) -> dict:
    """Rent fits for each terminal definition and locality steps along the levels
    (one representative module per level, in level order)."""
    fits: dict[str, RentFit] = {}
    for t in t_cols:
        sub = df[(df["gates"] > 0) & (df[t] > 0)]
        if len(sub) >= 2 and sub["gates"].nunique() >= 2:
            fits[t] = fit_rent(sub["gates"], sub[t], bootstrap=bootstrap)
    ordered = df[df["gates"] > 0].sort_values("level_index").drop_duplicates("level_index")
    steps: dict[str, list[dict]] = {}
    for t in t_cols:
        s = ordered[ordered[t] > 0]
        if len(s) >= 2:
            steps[t] = locality_steps(s["gates"].to_numpy(), s[t].to_numpy(), names=s["module"].tolist())
    return {"fits": fits, "steps": steps}
