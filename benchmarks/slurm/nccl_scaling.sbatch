#!/usr/bin/env bash
# NCCL collectives across N nodes (one rank per GPU). Submit with -N from submit_scaling_sweep.sh:
#   sbatch -N 4 --ntasks-per-node=$RR_GPUS_PER_NODE benchmarks/slurm/nccl_scaling.sbatch
#SBATCH --job-name=rr-nccl
#SBATCH --nodes=2
#SBATCH --exclusive
#SBATCH --time=00:30:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "$(dirname "$(scontrol show job "$SLURM_JOB_ID" | awk -F= '/Command=/{print $2}')")/common.sh" 2>/dev/null \
  || source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
rr_load_modules
RUN=$(rr_run_dir "nccl-N${SLURM_JOB_NUM_NODES}")
rr_write_meta "$RUN" "benchmark=nccl-tests" "message_max=8G"
echo "run dir: $RUN"
export NCCL_DEBUG=INFO NCCL_DEBUG_FILE="$RUN/nccl-debug.%h.%p"
rr_collectors_start "$RUN" 0.1
for test in all_reduce_perf alltoall_perf all_gather_perf; do
  bin="$RR_NCCL_TESTS_DIR/$test"
  [ -x "$bin" ] || { echo "missing $bin"; continue; }
  srun --mpi="$RR_MPI" --gres="$RR_GRES" rr_exec "$bin" -b 8 -e 8G -f 2 -g 1 -c 0 -n 20 -w 5 >"$RUN/$test.txt" 2>&1 || echo "$test failed" >>"$RUN/errors.txt"
done
rr_collectors_stop
echo "end_utc=$(date -u +%FT%TZ)" >>"$RUN/meta.json.tail"
echo "parse with: rentscale parse-nccl $RUN/alltoall_perf.txt"
