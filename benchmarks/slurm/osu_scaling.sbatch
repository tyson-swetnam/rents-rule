#!/usr/bin/env bash
# OSU MPI collectives and multi-pair bandwidth across N nodes.
#   sbatch -N 4 --ntasks-per-node=1 benchmarks/slurm/osu_scaling.sbatch   (one rank per node = fabric view)
#   sbatch -N 4 --ntasks-per-node=8 ...                                   (one rank per GPU/HCA rail)
#SBATCH --job-name=rr-osu
#SBATCH --nodes=2
#SBATCH --exclusive
#SBATCH --time=00:30:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
rr_load_modules
RUN=$(rr_run_dir "osu-N${SLURM_JOB_NUM_NODES}")
rr_write_meta "$RUN" "benchmark=osu"
rr_collectors_start "$RUN" 0.1
for t in collective/osu_alltoall collective/osu_allreduce collective/osu_allgather pt2pt/osu_mbw_mr; do
  bin="$RR_OSU_DIR/$t"
  [ -x "$bin" ] || { echo "missing $bin"; continue; }
  name=$(basename "$t")
  srun --mpi="$RR_MPI" rr_exec "$bin" -m 1:4194304 -f >"$RUN/$name.txt" 2>&1 || echo "$name failed" >>"$RUN/errors.txt"
done
rr_collectors_stop
echo "parse with: rentscale parse-osu $RUN/osu_alltoall.txt"
