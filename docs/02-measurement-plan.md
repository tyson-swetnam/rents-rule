# Measurement plan for CARC

Phased so that each step produces a usable dataset on its own. Phases 1 and 4 need no
exclusive resources; 2, 3, and 5 need reservations. Everything writes into
`runs/<UTC timestamp>-<label>-<jobid>/` with a `meta.json` (git SHA, job id, node list,
command line) written by `benchmarks/slurm/common.sh`.

## Phase 0 — desk work (no cluster access)

- Fill `docs/03-carc-hardware-inventory.md` from CARC documentation: clusters, node
  types, GPUs, HCAs, switch models, uplinks, storage, power/cooling plant.
- Check the `verify` rows in `hardware/reference/transistor_counts.csv` and
  `link_bandwidths.csv` against vendor whitepapers.
- Draft `hardware/reference/hierarchy_template.yaml` for each cluster with `TODO(carc)`
  placeholders.
- `make test` on a laptop to confirm the analysis stack.

## Phase 1 — static Rent census (login node + one `srun` per node type; no user impact)

```bash
bash hardware/inventory/slurm_inventory.sh runs/census          # sinfo/scontrol, topology plugin if configured
python hardware/inventory/parse_inventory.py --slurm runs/census # groups nodes into types → how many sruns
for p in <partitions>; do srun -p $p -N1 -c1 -t 10 bash hardware/inventory/inventory_node.sh runs/census; done
bash hardware/inventory/fabric_discover.sh runs/census           # ibnetdiscover/iblinkinfo; needs umad access
python hardware/inventory/parse_inventory.py runs/census         # per-node G and T
python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml --fabric runs/census/fabric/ibnetdiscover.txt
```

Access needed: `ibnetdiscover` requires read access to `/dev/infiniband/umad*` (root or
the `rdma` group) or can be run by ops on the subnet-manager host; `dmidecode` needs root
(optional). WAN uplink capacities come from UNM IT.

Output: `census.csv` (`level, module, G, T_lanes, T_ports, T_gbps`), fits for each `T`,
`λ_ℓ` profile, leaf-level Rent points straight from the fabric graph.

## Phase 2 — delivered bandwidth vs module size (exclusive nodes, hours)

Module sizes `n = 1, 2, 4, 8` GPUs within a node, then `16, 32, 64, …` across nodes.

```bash
sbatch benchmarks/slurm/p2p_intra_node.sbatch                  # NVLink/PCIe pairwise (nvbandwidth or p2pBandwidthLatencyTest)
bash   benchmarks/intra_node/nccl_local.sh                     # NCCL all_reduce/alltoall for g = 1,2,4,8 on one node
bash   benchmarks/slurm/submit_scaling_sweep.sh 2 4 8 16       # NCCL + OSU across N nodes
sbatch benchmarks/slurm/ib_perftest.sbatch                      # raw ib_write_bw / ib_write_lat between two nodes
```

Delivered terminal capacity of a module of `n` GPUs is `T_del(n) = n × busbw_alltoall(n)`
at the largest message size (NCCL "bus bandwidth" is per-rank injection bandwidth).
Fit `T_del` vs `G(n)` and compare with the installed `T` from Phase 1. Collectors run
beside each job, so Phase 2 also yields counter cross-checks (IB bytes ≈ what NCCL reports).

## Phase 3 — inference locality (exclusive GPU nodes, hours per configuration)

```bash
cp benchmarks/slurm/site.env.example benchmarks/slurm/site.env   # model path, modules/container, GPUs per node
sbatch benchmarks/slurm/inference_tp_pp.sbatch                   # TP ∈ {1,2,4,8} on one node, then PP across nodes
```

For each configuration: vLLM server → wait for health → start collectors (DCGM NVLink/PCIe
bytes, IB and NIC counters, power) → `load_generator.py` at several request rates and
length distributions → stop. Analysis: `rentscale rates` on counters, join with the
generator's token log, bytes/token per boundary, `p_w`, `λ_w`.

Multi-node PP needs a Ray cluster across nodes (template in the sbatch file); do TP-only
first — it already answers the node-boundary question.

## Phase 4 — passive traffic time series (days; one core per node; no exclusive access)

```bash
sbatch benchmarks/slurm/traffic_capture_passive.sbatch          # ib_counters.py + nic_counters.py at 100 ms for --time
bash   telemetry/collectors/switch_counters.sh runs/passive       # perfquery/SNMP on leaf and spine ports (ops)
```

Then `rentscale hurst`, per port and per aggregate. Ethics/ops: counters only; no
payloads; aggregate byte counts include other users' jobs but identify none of them.

## Phase 5 — power and cooling (with CARC operations / facilities)

- Node power is collected in Phases 2–3 (`power_sampler.py`).
- Facility: export PDU / UPS / chiller / pump metering and chilled-water ΔT and flow from
  the building management system for the same windows; compute partial PUE.
- Collect the floor plan and one-line electrical and mechanical diagrams to count network
  levels and lengths.

## Phase 6 — synthesis

`rentscale.scaling`: exponents per cost term, returns-to-scale table, `d_eff` profile,
size-tradeoff model. Compare with any hyperscaler / NAIRR data Melanie's group obtains
(the census YAML and the per-token normalization are the exchange formats).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Switch access denied | leaf-level `T` from `ibnetdiscover` run on a compute node with umad access; spine/core from ops-run `iblinkinfo` |
| 32-bit IB counters wrap in < 1 s at 200 Gb/s | collectors read the 64-bit sysfs counters; `rates_from_cumulative` handles wrap anyway |
| DCGM not installed | `nvlink_counters.py --backend nvidia-smi` (cumulative KiB per link) |
| Model does not fit one node | this is a *result* (forces TP across nodes and `λ_w → 1`); record it |
| Facility metering unavailable | node-level power still gives `P ∝ W^α`; PUE from public tables |
| Old nodes with Python 3.6 | collectors are stdlib-only and 3.6-compatible; analysis runs elsewhere |
