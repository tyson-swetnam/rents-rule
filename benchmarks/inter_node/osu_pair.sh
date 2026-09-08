#!/usr/bin/env bash
# Point-to-point OSU tests between the first two nodes of the current allocation.
#   salloc -N2 --exclusive ... ; bash benchmarks/inter_node/osu_pair.sh RUN_DIR
set -euo pipefail
RUN=${1:?RUN_DIR}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$HERE/../slurm/common.sh"
mkdir -p "$RUN"
for t in pt2pt/osu_bw pt2pt/osu_bibw pt2pt/osu_latency; do
  bin="$RR_OSU_DIR/$t"; [ -x "$bin" ] || { echo "missing $bin" >&2; continue; }
  srun -N2 -n2 --ntasks-per-node=1 --mpi="$RR_MPI" rr_exec "$bin" >"$RUN/$(basename "$t").txt" 2>&1 || true
done
