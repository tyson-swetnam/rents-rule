"""``rentscale`` command line: synthetic demo, Rent fits, Hurst estimates, counter rates,
census, benchmark parsers, node summaries, fabric summaries."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _print_fit(label: str, fit) -> None:
    print(f"  {label:<28s} {fit}")


def cmd_demo(args) -> int:
    from . import hurst, topology
    from .inventory import PKG_ROOT, census, census_report, format_edges, load_hierarchy

    print("Rent exponents of synthetic topologies (links vs gates)")
    ft = topology.fat_tree(8)
    pts = topology.rent_points(ft, topology.fat_tree_modules(ft))
    _print_fit("fat-tree k=8 (Al-Fares)", topology.fit_rent_points(pts))
    for k, r in ((16, 1), (16, 2), (16, 4)):
        tbl = topology.hierarchical_tree_table([k, k, k], oversubscription=r)
        fit = topology.fit_rent_points(tbl)
        _print_fit(f"tree k={k} r={r}:1  (analytic {topology.tapered_exponent(k, r):.3f})", fit)
    for d in (2, 3):
        tbl = topology.mesh_rent_points_analytic(d, [2, 4, 8, 16, 32])
        _print_fit(f"{d}-D mesh (analytic {topology.mesh_exponent(d):.3f})", topology.fit_rent_points(tbl))
    grid = topology.mesh(2, 16)
    bis = topology.recursive_bisection_points(grid, min_nodes=4)
    _print_fit("KL bisection of 16x16 grid", topology.fit_rent_points(bis))

    print("\nHurst estimates on synthetic fGn (n = 16384)")
    for H in (0.5, 0.7, 0.9):
        x = hurst.fgn(16384, H, seed=1)
        s = hurst.hurst_summary(x)
        print(
            f"  H={H:.1f}: R/S {s['rs']:.3f}  aggvar {s['aggvar']:.3f}  DFA {s['dfa1']:.3f}  "
            f"periodogram {s['periodogram']:.3f} (beta {s['beta']:.2f}, expect {hurst.beta_from_H(H):.2f})"
        )

    print("\nCensus of the illustrative 'example' hierarchy (public specs, not a real facility)")
    h = load_hierarchy(PKG_ROOT / "hardware" / "reference" / "hierarchy_template.yaml")
    df = census(h, group="example")
    with pd.option_context("display.width", 140, "display.float_format", "{:,.6g}".format):
        print(df[["level", "module", "gates", "lanes", "ports", "gbps"]].to_string(index=False))
    rep = census_report(df, hierarchy=h)
    for t, fit in rep["fits"].items():
        _print_fit(f"all levels, T = {t}", fit)
    print("  locality steps along parent <- child edges (T = gbps):")
    print(format_edges(rep["edges"], "gbps"))
    return 0


def cmd_fit_rent(args) -> int:
    from .rent import fit_rent

    df = pd.read_csv(args.csv)
    fit = fit_rent(df[args.g_col], df[args.t_col], bootstrap=args.bootstrap)
    print(fit)
    if args.json:
        print(json.dumps(fit.as_dict(), indent=2))
    return 0


def cmd_hurst(args) -> int:
    from . import hurst
    from .counters import rates_from_cumulative

    df = pd.read_csv(args.csv)
    col = args.column
    if args.cumulative:
        if not args.time_col:
            sys.exit("--cumulative needs --time-col")
        df = rates_from_cumulative(
            df, args.time_col, [col], group_cols=args.group_col.split(",") if args.group_col else None,
            wrap_bits=args.wrap_bits, multiplier=args.multiplier,
        )
        col = col + "_per_s"
    groups = [(None, df)] if not args.group_col else list(df.groupby(args.group_col.split(",")))
    for key, g in groups:
        x = g[col].to_numpy(dtype=float)
        s = hurst.hurst_summary(x)
        label = "" if key is None else f"{key}: "
        print(
            f"{label}n={np.isfinite(x).sum()}  R/S {s['rs']:.3f}  aggvar {s['aggvar']:.3f}  "
            f"DFA {s['dfa1']:.3f}  periodogram {s['periodogram']:.3f}  beta {s['beta']:.3f}  mean H {s['mean']:.3f}"
        )
    return 0


def cmd_rates(args) -> int:
    from .counters import rates_from_cumulative

    df = pd.read_csv(args.csv)
    out = rates_from_cumulative(
        df, args.time_col, args.cols.split(","),
        group_cols=args.group_cols.split(",") if args.group_cols else None,
        wrap_bits=args.wrap_bits, multiplier=args.multiplier,
    )
    if args.out:
        out.to_csv(args.out, index=False)
        print(f"wrote {args.out} ({len(out)} rows)")
    else:
        out.to_csv(sys.stdout, index=False)
    return 0


def cmd_census(args) -> int:
    from .inventory import census, census_report, format_edges, load_hierarchy, load_link_table, load_transistor_table

    h = load_hierarchy(args.yaml)
    tt = load_transistor_table(args.transistor_table)
    lt = load_link_table(args.link_table)
    df = census(h, tt, lt, group=args.group)
    if df.empty:
        print("no modules matched")
        return 1
    with pd.option_context("display.width", 160, "display.float_format", "{:,.6g}".format):
        print(df.to_string(index=False))
    for grp, sub in df.groupby("group"):
        rep = census_report(sub, bootstrap=args.bootstrap, hierarchy=h)
        print(f"\n[{grp}] Rent fits")
        for t, fit in rep["fits"].items():
            _print_fit(f"T = {t}", fit)
        for t in ("lanes", "gbps"):
            print(f"[{grp}] locality steps along parent <- child edges (T = {t})")
            print(format_edges(rep["edges"], t))
    if args.out:
        df.to_csv(args.out, index=False)
        print(f"\nwrote {args.out}")
    return 0


def cmd_fat_tree(args) -> int:
    from . import topology

    ft = topology.fat_tree(args.k)
    pts = topology.rent_points(ft, topology.fat_tree_modules(ft))
    summary = pts.groupby("level", sort=False)[["gates", "links", "capacity"]].first()
    print(summary.to_string())
    print(topology.fit_rent_points(pts))
    return 0


def cmd_tree(args) -> int:
    from . import topology

    fan = [int(v) for v in args.fanouts.split(",")]
    r = [float(v) for v in args.oversubscription.split(",")] if "," in args.oversubscription else float(args.oversubscription)
    tbl = topology.hierarchical_tree_table(fan, oversubscription=r)
    print(tbl.to_string(index=False))
    print(topology.fit_rent_points(tbl))
    return 0


def _parse_and_emit(parse_fn, path: str, out: str | None) -> int:
    df = parse_fn(Path(path).read_text(errors="replace"))
    if out:
        df.to_csv(out, index=False)
        print(f"wrote {out} ({len(df)} rows)")
    else:
        df.to_csv(sys.stdout, index=False)
    return 0


def cmd_parse_nccl(args) -> int:
    from .benchparse import nccl_peak_busbw, parse_nccl_tests

    text = Path(args.file).read_text(errors="replace")
    df = parse_nccl_tests(text)
    if args.out:
        df.to_csv(args.out, index=False)
    print(f"rows={len(df)} peak busbw (GB/s, out-of-place, largest size) = {nccl_peak_busbw(df):.3f}")
    return 0


def cmd_parse_osu(args) -> int:
    from .benchparse import parse_osu

    return _parse_and_emit(parse_osu, args.file, args.out)


def cmd_parse_perftest(args) -> int:
    from .benchparse import parse_perftest

    return _parse_and_emit(parse_perftest, args.file, args.out)


def cmd_node_summary(args) -> int:
    from .inventory import node_summary

    root = Path(args.dir)
    dirs = [root] if (root / "meta.txt").exists() else sorted(p for p in root.iterdir() if p.is_dir() and (p / "meta.txt").exists())
    rows = []
    for d in dirs:
        s = node_summary(d)
        rows.append(
            {
                "host": s["host"],
                "gpus": len(s["gpus"]),
                "cpu": (s["cpu"] or {}).get("model"),
                "gates": s["gates"],
                "lanes": s["terminals"]["lanes"],
                "ports": s["terminals"]["ports"],
                "gbps": s["terminals"]["gbps"],
                "unknown_parts": ";".join(s["unknown_parts"]),
                "missing": ";".join(s["missing"]),
            }
        )
        if args.json:
            (d / "summary.json").write_text(json.dumps(s, indent=2, default=str))
    with pd.option_context("display.width", 160):
        print(pd.DataFrame(rows).to_string(index=False))
    return 0


def cmd_fabric(args) -> int:
    from .fabric import fabric_summary, leaf_modules, parse_ibnetdiscover
    from .topology import fit_rent_points

    G = parse_ibnetdiscover(Path(args.file).read_text(errors="replace"))
    print(json.dumps(fabric_summary(G), indent=2))
    lm = leaf_modules(G)
    if not lm.empty:
        with pd.option_context("display.width", 160):
            print(lm.to_string(index=False))
        if lm["gates"].nunique() >= 2:
            print("leaf-level Rent fit (links vs hosts):", fit_rent_points(lm, t_col="links"))
        if args.out:
            lm.to_csv(args.out, index=False)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="rentscale", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="synthetic end-to-end demonstration").set_defaults(fn=cmd_demo)

    s = sub.add_parser("fit-rent", help="fit T = t G^p to a CSV")
    s.add_argument("csv")
    s.add_argument("--g-col", default="gates")
    s.add_argument("--t-col", default="links")
    s.add_argument("--bootstrap", type=int, default=500)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_fit_rent)

    s = sub.add_parser("hurst", help="Hurst / spectral estimates for a rate series")
    s.add_argument("csv")
    s.add_argument("--column", required=True)
    s.add_argument("--time-col")
    s.add_argument("--group-col", help="comma-separated grouping columns (e.g. dev,port)")
    s.add_argument("--cumulative", action="store_true", help="column is a cumulative counter")
    s.add_argument("--wrap-bits", type=int)
    s.add_argument("--multiplier", type=float, default=1.0)
    s.set_defaults(fn=cmd_hurst)

    s = sub.add_parser("rates", help="cumulative counters -> per-interval rates")
    s.add_argument("csv")
    s.add_argument("--time-col", required=True)
    s.add_argument("--cols", required=True, help="comma-separated counter columns")
    s.add_argument("--group-cols")
    s.add_argument("--wrap-bits", type=int)
    s.add_argument("--multiplier", type=float, default=1.0)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_rates)

    s = sub.add_parser("census", help="Rent census from a hierarchy YAML")
    s.add_argument("yaml")
    s.add_argument("--group")
    s.add_argument("--transistor-table")
    s.add_argument("--link-table")
    s.add_argument("--bootstrap", type=int, default=200)
    s.add_argument("--out")
    s.set_defaults(fn=cmd_census)

    s = sub.add_parser("fat-tree", help="Rent points of an Al-Fares k-ary fat-tree")
    s.add_argument("k", type=int)
    s.set_defaults(fn=cmd_fat_tree)

    s = sub.add_parser("tree", help="Rent points of a tapered switch tree")
    s.add_argument("--fanouts", default="32,32,16")
    s.add_argument("--oversubscription", default="2,1,1")
    s.set_defaults(fn=cmd_tree)

    for name, fn in (("parse-nccl", cmd_parse_nccl), ("parse-osu", cmd_parse_osu), ("parse-perftest", cmd_parse_perftest)):
        s = sub.add_parser(name, help=f"parse {name.split('-')[1]} output to CSV")
        s.add_argument("file")
        s.add_argument("--out")
        s.set_defaults(fn=fn)

    s = sub.add_parser("node-summary", help="gates and terminals from inventory_node.sh output")
    s.add_argument("dir", help="a node directory or the census root")
    s.add_argument("--json", action="store_true", help="also write summary.json per node")
    s.set_defaults(fn=cmd_node_summary)

    s = sub.add_parser("fabric", help="summarize an ibnetdiscover dump and its leaf-level Rent points")
    s.add_argument("file")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_fabric)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
