#!/usr/bin/env bash
# GPU<->GPU bandwidth matrix inside one node (NVLink / PCIe): nvbandwidth if configured,
# else CUDA samples p2pBandwidthLatencyTest; plus NCCL for g = 1,2,4,8 GPUs (intra_node/nccl_local.sh).
#SBATCH --job-name=rr-p2p
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --time=00:30:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
rr_load_modules
RUN=$(rr_run_dir "p2p")
rr_write_meta "$RUN" "benchmark=p2p-intra-node"
rr_collectors_start "$RUN" 0.1
nvidia-smi topo -m >"$RUN/topo.txt" 2>&1 || true
if [ -n "${RR_NVBANDWIDTH:-}" ] && [ -x "$RR_NVBANDWIDTH" ]; then
  for t in device_to_device_memcpy_read_ce device_to_device_memcpy_write_ce device_to_device_bidirectional_memcpy_read_ce host_to_device_memcpy_ce device_to_host_memcpy_ce; do
    rr_exec "$RR_NVBANDWIDTH" -t "$t" >"$RUN/nvbandwidth_$t.txt" 2>&1 || true
  done
elif command -v p2pBandwidthLatencyTest >/dev/null 2>&1; then
  rr_exec p2pBandwidthLatencyTest >"$RUN/p2pBandwidthLatencyTest.txt" 2>&1 || true
else
  echo "neither nvbandwidth nor p2pBandwidthLatencyTest available" >>"$RUN/errors.txt"
fi
bash "$RR_ROOT/benchmarks/intra_node/nccl_local.sh" "$RUN"
rr_collectors_stop
