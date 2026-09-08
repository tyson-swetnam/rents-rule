#!/usr/bin/env bash
# Sourced by every sbatch script: site settings, run directory + provenance, collector helpers.
RR_ROOT="${RR_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [ -f "$RR_ROOT/benchmarks/slurm/site.env" ]; then
  # shellcheck disable=SC1091
  source "$RR_ROOT/benchmarks/slurm/site.env"
else
  echo "WARN: $RR_ROOT/benchmarks/slurm/site.env not found; copy site.env.example" >&2
fi
RR_RUNS_DIR="${RR_RUNS_DIR:-$RR_ROOT/runs}"

rr_load_modules() {
  if [ -n "${RR_MODULES:-}" ] && [[ "${RR_MODULES}" != TODO* ]]; then
    # shellcheck disable=SC2086
    module load ${RR_MODULES} || echo "WARN: module load failed: $RR_MODULES" >&2
  fi
}

# rr_exec <cmd...>: run inside the container if RR_CONTAINER is set, else directly
rr_exec() {
  if [ -n "${RR_CONTAINER:-}" ]; then apptainer exec --nv "$RR_CONTAINER" "$@"; else "$@"; fi
}

# rr_run_dir <label> -> path of a fresh run directory
rr_run_dir() {
  local d="$RR_RUNS_DIR/$(date -u +%Y%m%dT%H%M%SZ)-$1-${SLURM_JOB_ID:-nojob}"
  mkdir -p "$d"; echo "$d"
}

# rr_write_meta <run_dir> [extra key=value ...]
rr_write_meta() {
  local d=$1; shift
  {
    echo "{"
    echo "  \"git_sha\": \"$(git -C "$RR_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)\","
    echo "  \"slurm_job_id\": \"${SLURM_JOB_ID:-}\","
    echo "  \"slurm_job_name\": \"${SLURM_JOB_NAME:-}\","
    echo "  \"nodelist\": \"${SLURM_JOB_NODELIST:-}\","
    echo "  \"num_nodes\": \"${SLURM_JOB_NUM_NODES:-}\","
    echo "  \"ntasks\": \"${SLURM_NTASKS:-}\","
    echo "  \"gpus_per_node\": \"${RR_GPUS_PER_NODE:-}\","
    echo "  \"partition\": \"${SLURM_JOB_PARTITION:-}\","
    echo "  \"start_utc\": \"$(date -u +%FT%TZ)\","
    echo "  \"argv\": \"$0 $*\","
    for kv in "$@"; do echo "  \"${kv%%=*}\": \"${kv#*=}\","; done
    echo "  \"host\": \"$(hostname)\""
    echo "}"
  } >"$d/meta.json"
}

# rr_collectors_start <run_dir> [interval] -> sets RR_COLL_PID
rr_collectors_start() {
  local d=$1 iv=${2:-0.1}
  srun --overlap --ntasks-per-node=1 --ntasks="${SLURM_JOB_NUM_NODES:-1}" --cpus-per-task=1 \
       bash "$RR_ROOT/telemetry/collectors/collect_all.sh" run "$d" "$iv" >"$d/collectors.log" 2>&1 &
  RR_COLL_PID=$!
  sleep 3
}

rr_collectors_stop() {
  [ -n "${RR_COLL_PID:-}" ] || return 0
  kill -TERM "$RR_COLL_PID" 2>/dev/null || true
  wait "$RR_COLL_PID" 2>/dev/null || true
}
