#!/usr/bin/env bash
# Inference locality: serve a model with vLLM at several tensor-parallel sizes on ONE node,
# drive it with the load generator at several request rates, and sample NVLink/PCIe/IB/NIC/
# power counters throughout. Multi-node pipeline parallelism: see the note at the bottom.
#SBATCH --job-name=rr-infer
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
rr_load_modules
RUN=$(rr_run_dir "infer")
rr_write_meta "$RUN" "benchmark=inference-tp-sweep" "model=$RR_MODEL"
PORT=${RR_VLLM_PORT:-8000}
for TP in ${RR_TP_LIST:-1 2 4 8}; do
  D="$RUN/tp$TP"; mkdir -p "$D"
  echo "=== TP=$TP -> $D"
  bash "$RR_ROOT/benchmarks/inference/run_vllm_server.sh" "$RR_MODEL" "$TP" "$PORT" "$D" &
  SERVER_PID=$!
  # wait for health
  for i in $(seq 1 180); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; sleep 5; done
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "server failed to start for TP=$TP" >>"$RUN/errors.txt"; kill "$SERVER_PID" 2>/dev/null || true; continue; }
  rr_collectors_start "$D" 0.1
  for rate in ${RR_INFER_RATES:-1 4 16}; do
    python3 "$RR_ROOT/benchmarks/inference/load_generator.py" --url "http://127.0.0.1:$PORT" --model "$RR_MODEL" \
      --rate "$rate" --duration "${RR_INFER_DURATION:-300}" --prompt-len 512 --output-len 128 \
      --output-len-dist fixed --out "$D/load_rate${rate}.csv" --summary "$D/load_rate${rate}.json" || true
    curl -s "http://127.0.0.1:$PORT/metrics" >"$D/vllm_metrics_rate${rate}.txt" 2>/dev/null || true
    sleep 20   # let queues drain between rates
  done
  rr_collectors_stop
  kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true
  sleep 10
done
echo "analysis: rentscale rates $RUN/tp8/<host>/gpu_dcgm.csv ...; join with load_rate*.csv token counts"

# Multi-node pipeline parallelism (PP) — run after the TP sweep works:
#   * request N nodes, start `ray start --head` on node 0 and `ray start --address=<head>:6379` on
#     the others (srun -N1 -w <node>), then launch vLLM with --tensor-parallel-size <GPUs/node>
#     --pipeline-parallel-size N and --distributed-executor-backend ray;
#   * collectors on every node via rr_collectors_start (it already uses --ntasks-per-node=1);
#   * the node-boundary bytes/token then come from ib_counters.csv on each node.
