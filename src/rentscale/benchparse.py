"""Parsers for benchmark outputs: nccl-tests, OSU micro-benchmarks, perftest (ib_*_bw)."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


def _num(tok: str):
    try:
        return int(tok)
    except ValueError:
        try:
            return float(tok)
        except ValueError:
            return tok


def _is_num(tok: str) -> bool:
    try:
        float(tok)
        return True
    except ValueError:
        return False


def _dedupe(names: list[str]) -> list[str]:
    counts = {n: names.count(n) for n in names}
    seen: dict[str, int] = {}
    out = []
    for n in names:
        base = n.lstrip("#")
        if counts[n] > 1:
            k = seen.get(n, 0)
            seen[n] = k + 1
            out.append(f"{base}_oop" if k == 0 else f"{base}_ip")
        else:
            out.append(base)
    return out


def parse_nccl_tests(text: str) -> pd.DataFrame:
    """Parse ``all_reduce_perf`` / ``alltoall_perf`` / ... output. Columns follow the
    header (``size count type redop root time algbw busbw wrong`` with ``_oop`` /
    ``_ip`` suffixes for out-of-place / in-place). Bandwidths are GB/s, time in us."""
    header: list[str] | None = None
    rows = []
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        if s.lstrip().startswith("#"):
            toks = s.lstrip("#").split()
            if "size" in toks and "busbw" in toks:
                header = _dedupe(toks)
            continue
        toks = s.split()
        if header is None or not toks or not _is_num(toks[0]):
            continue
        if len(toks) != len(header):
            continue
        rows.append({name: _num(v) for name, v in zip(header, toks, strict=True)})
    return pd.DataFrame(rows)


_AVG_BUSBW_RE = re.compile(r"#\s*Avg bus bandwidth\s*:\s*([\d.]+)")


def nccl_avg_bus_bandwidth(text: str) -> float | None:
    m = _AVG_BUSBW_RE.search(text)
    return float(m.group(1)) if m else None


def nccl_peak_busbw(df: pd.DataFrame) -> float:
    """Bus bandwidth (GB/s) at the largest message size, out-of-place."""
    if df.empty:
        return float("nan")
    col = "busbw_oop" if "busbw_oop" in df.columns else "busbw"
    return float(df.sort_values("size").iloc[-1][col])


def delivered_terminal_capacity(n_ranks: int, busbw_gbs: float) -> float:
    """``T_del = n × busbw``: aggregate injection bandwidth a module of ``n`` ranks achieved."""
    return float(n_ranks) * float(busbw_gbs)


def parse_osu(text: str) -> pd.DataFrame:
    """Parse OSU micro-benchmark output (``# Size <metric>`` header, numeric rows).
    ``value`` is the first numeric column; extra columns (``-f``: min/max/iterations, or
    ``osu_mbw_mr``'s messages/s) become ``value2``.. Metric and title in ``df.attrs``."""
    metric = title = None
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            body = s.lstrip("#").strip()
            if body.lower().startswith("osu"):
                title = body
            elif body.lower().startswith("size"):
                metric = body
            continue
        toks = s.split()
        if len(toks) >= 2 and _is_num(toks[0]) and _is_num(toks[1]):
            row = {"size": float(toks[0]), "value": float(toks[1])}
            for i, t in enumerate(toks[2:6], start=2):
                if _is_num(t):
                    row[f"value{i}"] = float(t)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.attrs["metric"] = metric
    df.attrs["title"] = title
    return df


def parse_perftest(text: str) -> pd.DataFrame:
    """Parse ``ib_write_bw`` / ``ib_read_bw`` / ``ib_send_bw`` tables. Bandwidth units are
    whatever the run used (MB/s by default, Gb/s with ``--report_gbits``); the header
    text is kept in ``df.attrs['header']``."""
    rows = []
    header = None
    in_table = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#bytes"):
            header = s
            in_table = True
            continue
        if not in_table:
            continue
        toks = s.split()
        if len(toks) >= 4 and _is_num(toks[0]):
            rows.append(
                {
                    "bytes": int(float(toks[0])),
                    "iterations": int(float(toks[1])),
                    "bw_peak": float(toks[2]),
                    "bw_avg": float(toks[3]),
                    "msg_rate_mpps": float(toks[4]) if len(toks) > 4 and _is_num(toks[4]) else np.nan,
                }
            )
        elif s.startswith("---") and rows:
            in_table = False
    df = pd.DataFrame(rows)
    df.attrs["header"] = header
    return df
