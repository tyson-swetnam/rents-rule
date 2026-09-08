#!/usr/bin/env bash
# Cluster-level inventory from Slurm (run on a login node):
#   bash hardware/inventory/slurm_inventory.sh [OUT_ROOT]   (default runs/census)
# Produces OUT_ROOT/slurm/{nodes.txt,partitions.txt,scontrol_nodes.txt,topology.txt,...}
set -u
OUT="${1:-runs/census}/slurm"
mkdir -p "$OUT"
have() { command -v "$1" >/dev/null 2>&1; }
if ! have sinfo; then echo "sinfo not found: not a Slurm login node?" >&2; exit 1; fi

sinfo -N -o "%N %P %c %m %G %f %T" >"$OUT/nodes.txt" 2>"$OUT/nodes.err"
sinfo -s                              >"$OUT/partitions_summary.txt" 2>/dev/null
scontrol show partition               >"$OUT/partitions.txt" 2>/dev/null
scontrol show node                    >"$OUT/scontrol_nodes.txt" 2>/dev/null
scontrol show topology                >"$OUT/topology.txt" 2>"$OUT/topology.err" || true
scontrol show config | grep -i -E "topology|gres|select|cluster" >"$OUT/config_excerpt.txt" 2>/dev/null
{ echo "date_utc=$(date -u +%FT%TZ)"; echo "cluster=${SLURM_CLUSTER_NAME:-$(scontrol show config 2>/dev/null | awk -F= '/ClusterName/{gsub(/ /,"",$2);print $2}')}"; } >"$OUT/meta.txt"
echo "wrote $OUT:"; ls -1 "$OUT"
