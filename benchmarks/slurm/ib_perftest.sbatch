#!/usr/bin/env bash
# Raw RDMA bandwidth and latency between two nodes (perftest ib_write_bw / ib_write_lat).
#SBATCH --job-name=rr-perftest
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
rr_load_modules
RUN=$(rr_run_dir "perftest")
rr_write_meta "$RUN" "benchmark=perftest" "ib_device=$RR_IB_DEVICE"
mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
SERVER=${NODES[0]}; CLIENT=${NODES[1]}
BWBIN="${RR_PERFTEST_DIR:+$RR_PERFTEST_DIR/}ib_write_bw"
LATBIN="${RR_PERFTEST_DIR:+$RR_PERFTEST_DIR/}ib_write_lat"
rr_collectors_start "$RUN" 0.1
for size in 4096 65536 1048576 8388608; do
  srun -N1 -n1 -w "$SERVER" "$BWBIN" -d "$RR_IB_DEVICE" -F --report_gbits -s "$size" -D 5 >"$RUN/bw_server_$size.txt" 2>&1 &
  sleep 3
  srun -N1 -n1 -w "$CLIENT" "$BWBIN" -d "$RR_IB_DEVICE" -F --report_gbits -s "$size" -D 5 "$SERVER" >"$RUN/bw_client_$size.txt" 2>&1 || true
  wait
done
srun -N1 -n1 -w "$SERVER" "$LATBIN" -d "$RR_IB_DEVICE" -F -s 8 -n 10000 >"$RUN/lat_server.txt" 2>&1 &
sleep 3
srun -N1 -n1 -w "$CLIENT" "$LATBIN" -d "$RR_IB_DEVICE" -F -s 8 -n 10000 "$SERVER" >"$RUN/lat_client.txt" 2>&1 || true
wait
rr_collectors_stop
echo "parse with: rentscale parse-perftest $RUN/bw_client_1048576.txt"
