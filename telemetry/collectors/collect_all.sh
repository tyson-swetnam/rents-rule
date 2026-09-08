#!/usr/bin/env bash
# Start/stop every collector on this node, writing into RUN_DIR/<host>/.
#
#   collect_all.sh run   RUN_DIR [INTERVAL]   # foreground until SIGTERM (use under `srun --overlap ... &`)
#   collect_all.sh start RUN_DIR [INTERVAL]   # background with pid files
#   collect_all.sh stop  RUN_DIR
#
# Collectors: ib_counters.py, nic_counters.py, nvlink_counters.py (dcgmi, else nvidia-smi),
# power_sampler.py (1 s). Each degrades gracefully when its source is absent.
set -u
MODE=${1:?run|start|stop}; RUN_DIR=${2:?RUN_DIR}; INTERVAL=${3:-0.1}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HOST=$(hostname -s 2>/dev/null || hostname)
D="$RUN_DIR/$HOST"
mkdir -p "$D"
PY=${PYTHON:-python3}
PIDS=()

start_collectors() {
  $PY "$HERE/ib_counters.py"  --interval "$INTERVAL" --out "$D/ib_counters.csv"  2>"$D/ib_counters.err"  & PIDS+=($!); echo $! >"$D/ib_counters.pid"
  $PY "$HERE/nic_counters.py" --interval "$INTERVAL" --out "$D/nic_counters.csv" 2>"$D/nic_counters.err" & PIDS+=($!); echo $! >"$D/nic_counters.pid"
  if command -v dcgmi >/dev/null 2>&1; then
    $PY "$HERE/nvlink_counters.py" --backend dcgmi --interval "$INTERVAL" --out "$D/gpu_dcgm.csv" 2>"$D/gpu_dcgm.err" & PIDS+=($!); echo $! >"$D/gpu_dcgm.pid"
  elif command -v nvidia-smi >/dev/null 2>&1; then
    $PY "$HERE/nvlink_counters.py" --backend nvidia-smi --interval 0.5 --out "$D/gpu_nvsmi.txt" 2>"$D/gpu_nvsmi.err" & PIDS+=($!); echo $! >"$D/gpu_nvsmi.pid"
  fi
  $PY "$HERE/power_sampler.py" --interval 1 --out "$D/power.csv" 2>"$D/power.err" & PIDS+=($!); echo $! >"$D/power.pid"
  { echo "host=$HOST"; echo "start_utc=$(date -u +%FT%TZ)"; echo "interval=$INTERVAL"; echo "slurm_job_id=${SLURM_JOB_ID:-}"; echo "slurm_step_id=${SLURM_STEP_ID:-}"; } >"$D/collect_meta.txt"
}

stop_collectors() {
  for f in "$D"/*.pid; do
    [ -f "$f" ] || continue
    pid=$(cat "$f"); kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 1
  for f in "$D"/*.pid; do [ -f "$f" ] && { pid=$(cat "$f"); kill -KILL "$pid" 2>/dev/null || true; rm -f "$f"; }; done
  echo "stop_utc=$(date -u +%FT%TZ)" >>"$D/collect_meta.txt"
}

case "$MODE" in
  start) start_collectors; echo "collectors started in $D" ;;
  stop)  stop_collectors;  echo "collectors stopped ($D)" ;;
  run)
    trap 'stop_collectors; exit 0' TERM INT
    start_collectors
    echo "collectors running in $D (pid $$); waiting for SIGTERM"
    while :; do sleep 1; done ;;
  *) echo "mode must be run|start|stop" >&2; exit 1 ;;
esac
