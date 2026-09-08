#!/usr/bin/env bash
# Passive traffic time series for the Hurst analysis: sample IB and NIC counters on one node
# at 100 ms for the job's duration. One core, no GPUs. Counters only — no payloads.
#   sbatch --nodelist=<node> --time=24:00:00 benchmarks/slurm/traffic_capture_passive.sbatch
# If the partition does not allow node sharing, ask CARC ops to run ib_counters.py as a service.
#SBATCH --job-name=rr-passive
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
source "${RR_ROOT:-$(pwd)}/benchmarks/slurm/common.sh"
RUN=$(rr_run_dir "passive")
rr_write_meta "$RUN" "benchmark=passive-capture" "interval=0.1"
# leave ~2 minutes of headroom before the walltime so files are flushed and closed
LIMIT=$(( $(squeue -h -j "$SLURM_JOB_ID" -o %l | awk -F'[-:]' '{ if (NF==4) print $1*86400+$2*3600+$3*60+$4; else if (NF==3) print $1*3600+$2*60+$3; else print $1*60+$2 }') - 120 ))
[ "$LIMIT" -gt 60 ] || LIMIT=3600
D="$RUN/$(hostname -s)"; mkdir -p "$D"
python3 "$RR_ROOT/telemetry/collectors/ib_counters.py"  --interval 0.1 --duration "$LIMIT" --out "$D/ib_counters.csv" &
python3 "$RR_ROOT/telemetry/collectors/nic_counters.py" --interval 0.1 --duration "$LIMIT" --out "$D/nic_counters.csv" &
wait
echo "analysis: rentscale hurst $D/ib_counters.csv --column port_xmit_data --cumulative --time-col t_mono --group-col dev,port --multiplier 4"
