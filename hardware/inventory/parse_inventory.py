#!/usr/bin/env python3
"""Summarize census inventories.

    python hardware/inventory/parse_inventory.py runs/census           # per-node gates & terminals
    python hardware/inventory/parse_inventory.py --slurm runs/census   # group Slurm nodes into types

Runs without installing the package (adds ../../src to sys.path).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "src"))


def slurm_types(root: Path) -> int:
    nodes = root / "slurm" / "nodes.txt"
    if not nodes.exists():
        print(f"{nodes} not found; run slurm_inventory.sh first", file=sys.stderr)
        return 1
    groups: dict[tuple, list[str]] = defaultdict(list)
    for line in nodes.read_text().splitlines()[1:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        name, part, cpus, mem, gres, feats, state = parts[:7]
        groups[(part, cpus, mem, gres, feats)].append(name)
    print(f"{'partition':<14s} {'cpus':>5s} {'mem_MB':>9s} {'gres':<24s} {'features':<30s} {'count':>5s}  example")
    out = []
    for (part, cpus, mem, gres, feats), names in sorted(groups.items()):
        print(f"{part:<14s} {cpus:>5s} {mem:>9s} {gres:<24s} {feats:<30s} {len(names):>5d}  {names[0]}")
        out.append({"partition": part, "cpus": cpus, "mem_mb": mem, "gres": gres, "features": feats, "count": len(names), "example": names[0], "nodes": names})
    (root / "slurm" / "node_types.json").write_text(json.dumps(out, indent=2))
    print(f"\n{len(out)} node types -> {root / 'slurm' / 'node_types.json'}")
    print("run inventory_node.sh on the 'example' node of each type (srun --nodelist=<example> ...)")
    return 0


def node_summaries(root: Path) -> int:
    from rentscale.inventory import node_summary

    dirs = sorted(p for p in root.iterdir() if p.is_dir() and (p / "meta.txt").exists())
    if not dirs:
        print(f"no node directories with meta.txt under {root}", file=sys.stderr)
        return 1
    print(f"{'host':<16s} {'gpus':>4s} {'gates':>12s} {'lanes':>6s} {'ports':>6s} {'gbps':>8s}  cpu / unknown parts")
    for d in dirs:
        s = node_summary(d)
        (d / "summary.json").write_text(json.dumps(s, indent=2, default=str))
        t = s["terminals"]
        cpu = (s["cpu"] or {}).get("model") or "?"
        unk = f"  UNKNOWN: {';'.join(s['unknown_parts'])}" if s["unknown_parts"] else ""
        print(f"{s['host']:<16s} {len(s['gpus']):>4d} {s['gates']:>12.3e} {t['lanes']:>6.0f} {t['ports']:>6d} {t['gbps']:>8.0f}  {cpu}{unk}")
    print("\nper-node summary.json written; feed the numbers into hardware/reference/hierarchy_template.yaml")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="census root (e.g. runs/census)")
    ap.add_argument("--slurm", action="store_true", help="group Slurm nodes into types instead")
    a = ap.parse_args()
    root = Path(a.root)
    return slurm_types(root) if a.slurm else node_summaries(root)


if __name__ == "__main__":
    sys.exit(main())
