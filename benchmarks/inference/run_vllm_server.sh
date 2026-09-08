#!/usr/bin/env bash
# Start a vLLM OpenAI-compatible server. Usage: run_vllm_server.sh MODEL TP PORT OUT_DIR
# Runs in the foreground (the sbatch script backgrounds it and kills it when done).
set -euo pipefail
MODEL=${1:?MODEL}; TP=${2:-1}; PORT=${3:-8000}; OUT=${4:-.}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$HERE/../slurm/common.sh"
mkdir -p "$OUT"
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-$(seq -s, 0 $((TP - 1)))}
exec rr_exec python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --tensor-parallel-size "$TP" --port "$PORT" --host 127.0.0.1 \
  --disable-log-requests --max-model-len 4096 --gpu-memory-utilization 0.9 \
  >"$OUT/vllm_server.log" 2>&1
