"""Turn cumulative hardware counters into rates, and parse the text outputs of
``nvidia-smi nvlink -gt d``, ``dcgmi dmon``, and ``ethtool -S``."""
from __future__ import annotations

import re
from typing import Sequence

import numpy as np
import pandas as pd

#: ``port_xmit_data`` / ``port_rcv_data`` in /sys/class/infiniband are in units of 4 octets.
IB_DATA_OCTET_UNITS = 4


def rates_from_cumulative(
    df: pd.DataFrame,
    time_col: str,
    value_cols: Sequence[str],
    group_cols: Sequence[str] | None = None,
    wrap_bits: int | None = None,
    multiplier: float = 1.0,
    suffix: str = "_per_s",
) -> pd.DataFrame:
    """Per-interval rates from cumulative counters.

    Rows are sorted by ``time_col`` within each group. A negative delta is treated as a
    counter wrap (``+ 2**wrap_bits``) when ``wrap_bits`` is given, else as invalid (NaN).
    ``multiplier`` converts units (e.g. 4 for IB ``port_*_data``). Output has one row per
    interval with ``dt_s`` and ``<col><suffix>`` columns; the first row of each group is
    dropped.
    """
    value_cols = list(value_cols)
    group_cols = list(group_cols or [])

    def _one(g: pd.DataFrame) -> pd.DataFrame:
        g = g.sort_values(time_col)
        t = g[time_col].to_numpy(dtype=float)
        dt = np.diff(t)
        out = g.iloc[1:].copy()
        out["dt_s"] = dt
        for c in value_cols:
            d = np.diff(g[c].to_numpy(dtype=float))
            if wrap_bits:
                d = np.where(d < 0, d + 2.0**wrap_bits, d)
            else:
                d = np.where(d < 0, np.nan, d)
            with np.errstate(divide="ignore", invalid="ignore"):
                out[c + suffix] = d * multiplier / dt
        return out

    if group_cols:
        parts = [_one(g) for _, g in df.groupby(group_cols, sort=False)]
        return pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    return _one(df).reset_index(drop=True)


# ----------------------------------------------------------------------------- nvidia-smi
_GPU_RE = re.compile(r"^GPU\s+(\d+):")
_LINK_RE = re.compile(
    r"Link\s+(\d+):\s*Data\s+(Tx|Rx):\s*([\d.]+)\s*(B|KiB|MiB|GiB|KB|MB|GB)?", re.IGNORECASE
)
_UNIT = {
    "": 1,
    "b": 1,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
}


def parse_nvidia_smi_nvlink_throughput(text: str) -> pd.DataFrame:
    """Parse ``nvidia-smi nvlink -gt d`` (cumulative data bytes per link, per direction)."""
    gpu = None
    rows: dict[tuple[int, int], dict] = {}
    for line in text.splitlines():
        m = _GPU_RE.match(line.strip())
        if m:
            gpu = int(m.group(1))
            continue
        m = _LINK_RE.search(line)
        if m and gpu is not None:
            link = int(m.group(1))
            direction = m.group(2).lower()
            val = float(m.group(3)) * _UNIT[(m.group(4) or "").lower()]
            rows.setdefault((gpu, link), {"gpu": gpu, "link": link})[f"{direction}_bytes"] = val
    return pd.DataFrame(sorted(rows.values(), key=lambda r: (r["gpu"], r["link"])))


# ----------------------------------------------------------------------------- dcgmi
def parse_dcgmi_dmon(text: str) -> pd.DataFrame:
    """Parse ``dcgmi dmon`` output (header ``#Entity <fields>``, rows ``GPU <id> <values>``).
    Values are as reported by DCGM (profiling byte fields are rates over the sample)."""
    header: list[str] | None = None
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#Entity") or s.startswith("# Entity"):
            header = s.lstrip("#").split()[1:]
            continue
        if not s or s == "ID" or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) >= 2 and parts[0] in ("GPU", "Switch", "CPU"):
            vals = parts[2:]
            names = header if header and len(header) == len(vals) else [f"f{i}" for i in range(len(vals))]
            row: dict = {"entity": parts[0], "id": int(parts[1])}
            for name, v in zip(names, vals, strict=True):
                try:
                    row[name] = float(v)
                except ValueError:
                    row[name] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- ethtool
_STAT_RE = re.compile(r"^\s*([A-Za-z0-9_.\[\]\-]+):\s*(-?\d+)\s*$")


def parse_ethtool_stats(text: str) -> dict[str, int]:
    """Parse ``ethtool -S <iface>`` into ``{counter: value}``."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = _STAT_RE.match(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


# ----------------------------------------------------------------------------- locality
def bytes_per_unit_work(total_bytes: float, work_units: float) -> float:
    if work_units <= 0:
        return float("nan")
    return float(total_bytes) / float(work_units)


def locality_fractions(bytes_by_level: dict[str, float], order: Sequence[str]) -> pd.DataFrame:
    """Given bytes crossing each boundary (ordered inner -> outer), return per level the
    share of total and ``lambda`` = bytes at this level / bytes at the level below."""
    total = float(sum(bytes_by_level.get(lv, 0.0) for lv in order))
    rows = []
    prev = None
    for lv in order:
        b = float(bytes_by_level.get(lv, 0.0))
        rows.append(
            {
                "level": lv,
                "bytes": b,
                "fraction_of_total": b / total if total > 0 else np.nan,
                "lambda": (b / prev) if prev else np.nan,
            }
        )
        prev = b
    return pd.DataFrame(rows)
