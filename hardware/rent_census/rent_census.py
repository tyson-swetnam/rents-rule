#!/usr/bin/env python3
"""Rent census: resolve a hierarchy YAML into (G, T) per module, fit p for lanes / ports /
Gb/s, print the locality-step profile, and optionally add leaf-level points from an
ibnetdiscover dump.

    python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml --group example
    python hardware/rent_census/rent_census.py hierarchy.yaml --group carc --fabric runs/census/fabric/ibnetdiscover.txt --out census.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "src"))

import pandas as pd  # noqa: E402

from rentscale.fabric import fabric_summary, leaf_modules, parse_ibnetdiscover  # noqa: E402
from rentscale.inventory import (  # noqa: E402
    census,
    census_report,
    load_hierarchy,
    load_link_table,
    load_transistor_table,
)
from rentscale.topology import fit_rent_points  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yaml")
    ap.add_argument("--group", help="only modules of this group (e.g. example, carc)")
    ap.add_argument("--fabric", help="ibnetdiscover.txt for leaf-level points")
    ap.add_argument("--gates-per-host", type=float, default=1.0, help="gates per HCA for the fabric points (e.g. node transistor count)")
    ap.add_argument("--transistor-table")
    ap.add_argument("--link-table")
    ap.add_argument("--bootstrap", type=int, default=500)
    ap.add_argument("--out", help="write census.csv")
    a = ap.parse_args()

    h = load_hierarchy(a.yaml)
    df = census(h, load_transistor_table(a.transistor_table), load_link_table(a.link_table), group=a.group)
    if df.empty:
        print("no modules matched (check --group)")
        return 1
    with pd.option_context("display.width", 180, "display.float_format", "{:,.6g}".format):
        print(df.to_string(index=False))
    todo = df[(df["gates"] == 0) | df["unknown_parts"].astype(bool)]
    if not todo.empty:
        print(f"\n{len(todo)} module(s) have zero gates or unresolved parts — fill hierarchy TODOs / reference tables:")
        print("   " + ", ".join(todo["module"].tolist()))

    for grp, sub in df.groupby("group"):
        rep = census_report(sub, bootstrap=a.bootstrap)
        print(f"\n[{grp}] Rent fits across levels")
        for t, fit in rep["fits"].items():
            print(f"  T = {t:<6s} {fit}")
        for t, steps in rep["steps"].items():
            print(f"[{grp}] locality steps, T = {t}")
            for st in steps:
                print(f"    {st['from']:<26s} -> {st['to']:<26s} children={st['children']:>8.0f}  local p={st['local_exponent']:>7.3f}  lambda={st['lambda']:.4g}")

    if a.fabric:
        G = parse_ibnetdiscover(Path(a.fabric).read_text(errors="replace"))
        print("\nfabric:", fabric_summary(G))
        lm = leaf_modules(G, gates_for_host=lambda desc: a.gates_per_host)
        if not lm.empty:
            with pd.option_context("display.width", 180):
                print(lm.to_string(index=False))
            if lm["gates"].nunique() >= 2:
                print("leaf-level fit (uplinks vs gates):", fit_rent_points(lm, t_col="links"))
            print(f"oversubscription (down/up Gb/s) per leaf: median {lm['oversubscription'].median():.2f}")
    if a.out:
        df.to_csv(a.out, index=False)
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
