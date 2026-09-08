#!/usr/bin/env bash
# TCP throughput over the Ethernet (management / campus) path between two nodes — the
# facility-boundary analogue of ib_perftest. Usage inside a 2-node allocation:
#   bash benchmarks/inter_node/iperf3_pair.sh RUN_DIR [parallel_streams]
set -euo pipefail
RUN=${1:?RUN_DIR}; P=${2:-8}
mkdir -p "$RUN"
mapfile -t NODES < <(scontrol show hostnames "$SLURM_JOB_NODELIST")
SERVER=${NODES[0]}; CLIENT=${NODES[1]}
srun -N1 -n1 -w "$SERVER" iperf3 -s -1 -J >"$RUN/iperf3_server.json" 2>&1 &
sleep 3
srun -N1 -n1 -w "$CLIENT" iperf3 -c "$SERVER" -P "$P" -t 30 -J >"$RUN/iperf3_client.json" 2>&1 || true
wait
