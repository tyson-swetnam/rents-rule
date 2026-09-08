# telemetry/ — passive counter collectors

Stdlib-only Python (3.6+) and bash, so they run on any node without installing anything.
They read **counters only** — bytes and packets — never payloads, and never anything that
identifies another user's job.

| collector | source | output |
|---|---|---|
| `ib_counters.py` | `/sys/class/infiniband/<dev>/ports/<p>/counters/{port_xmit_data,port_rcv_data,port_xmit_packets,port_rcv_packets}` (cumulative; `*_data` in 4-byte units) | CSV, one row per (sample, dev, port) |
| `nic_counters.py` | `/sys/class/net/<iface>/statistics/{rx_bytes,tx_bytes,rx_packets,tx_packets}` | CSV |
| `nvlink_counters.py` | `dcgmi dmon -e 1011,1012,1009,1010,...` (NVLink/PCIe bytes, rates) or `nvidia-smi nvlink -gt d` (cumulative KiB per link) | CSV |
| `power_sampler.py` | `nvidia-smi --query-gpu=power.draw`, RAPL `energy_uj`, optional `ipmitool dcmi power reading` | CSV (long format) |
| `switch_counters.sh` | `perfquery -x LID PORT` (InfiniBand, needs umad) or SNMP `IF-MIB::ifHCInOctets` (Ethernet) | CSV |
| `collect_all.sh` | starts/stops the above on one node into `RUN_DIR/<host>/` | pid files + logs |

## Use inside a Slurm job

```bash
RUN=runs/$(date -u +%Y%m%dT%H%M%SZ)-mytest-$SLURM_JOB_ID
srun --overlap --ntasks-per-node=1 bash telemetry/collectors/collect_all.sh run "$RUN" 0.1 &
COLL=$!
srun ... <workload> ...
kill -TERM $COLL; wait $COLL
```

`run` mode stays in the foreground until SIGTERM so the srun step (and its GPU/IB
visibility) stays alive alongside the workload. Interactive use: `start` / `stop`.

## Analysis

```bash
rentscale rates runs/<id>/<host>/ib_counters.csv --time-col t_mono --cols port_xmit_data,port_rcv_data \
          --group-cols dev,port --multiplier 4 --out ib_rates.csv
rentscale hurst ib_rates.csv --column port_xmit_data_per_s
```
