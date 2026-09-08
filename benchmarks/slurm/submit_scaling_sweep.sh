#!/usr/bin/env bash
# Submit the NCCL and OSU scaling jobs for several node counts:
#   bash benchmarks/slurm/submit_scaling_sweep.sh 2 4 8 16
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export RR_ROOT="${RR_ROOT:-$(cd "$HERE/../.." && pwd)}"
source "$HERE/common.sh"
[ $# -gt 0 ] || { echo "usage: $0 N1 [N2 ...]"; exit 1; }
extra=()
[ -n "${RR_PARTITION:-}" ] && [[ "$RR_PARTITION" != TODO* ]] && extra+=(-p "$RR_PARTITION")
[ -n "${RR_ACCOUNT:-}" ] && extra+=(--account "$RR_ACCOUNT")
[ -n "${RR_QOS:-}" ] && extra+=(--qos "$RR_QOS")
for N in "$@"; do
  sbatch "${extra[@]}" -N "$N" --ntasks-per-node="${RR_GPUS_PER_NODE:-1}" --gres="${RR_GRES:-gpu:1}" --export=ALL,RR_ROOT "$HERE/nccl_scaling.sbatch"
  sbatch "${extra[@]}" -N "$N" --ntasks-per-node=1 --export=ALL,RR_ROOT "$HERE/osu_scaling.sbatch"
done
