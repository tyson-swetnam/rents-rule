#!/usr/bin/env bash
# NCCL collectives for g = 1, 2, 4, 8 GPUs inside one node (single process, -g N):
# module sizes below the node boundary. Usage: nccl_local.sh RUN_DIR
set -euo pipefail
RUN=${1:?RUN_DIR}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$HERE/../slurm/common.sh"
NG=$(nvidia-smi --list-gpus 2>/dev/null | wc -l || echo 0)
[ "$NG" -gt 0 ] || { echo "no GPUs visible" >&2; exit 0; }
for test in all_reduce_perf alltoall_perf; do
  bin="$RR_NCCL_TESTS_DIR/$test"
  [ -x "$bin" ] || { echo "missing $bin" >&2; continue; }
  g=1
  while [ "$g" -le "$NG" ]; do
    rr_exec "$bin" -b 8 -e 8G -f 2 -g "$g" -c 0 -n 20 -w 5 >"$RUN/${test}_g${g}.txt" 2>&1 || echo "$test g=$g failed" >>"$RUN/errors.txt"
    g=$((g * 2))
  done
done
echo "T_del(n) = n x busbw at the largest size: rentscale parse-nccl $RUN/alltoall_perf_g8.txt"
