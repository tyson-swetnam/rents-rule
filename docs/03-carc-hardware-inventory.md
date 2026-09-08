# CARC hardware inventory

Everything here comes from the CARC documentation site (https://carc.unm.edu/docs — an OKF
bundle whose hardware pages were generated 2026-08-29 from cluster state observed
2026-07-25) unless marked otherwise. Fields marked `TODO(carc)` are **not documented** and
must come from the inventory scripts (`hardware/inventory/*.sh`) run on the clusters.
The same numbers are encoded in `hardware/reference/hierarchy_template.yaml` (group
`carc`) and `data/reference/carc_generations.csv`.

Sources: [systems/overview](https://carc.unm.edu/docs/systems/overview/),
[about/facilities](https://carc.unm.edu/docs/about/facilities/),
[systems/resource-limits](https://carc.unm.edu/docs/systems/resource-limits/),
[running-jobs/slurm-intro](https://carc.unm.edu/docs/running-jobs/slurm-intro/),
[systems/cluster-specifications](https://carc.unm.edu/docs/systems/cluster-specifications/) (legacy),
[running-jobs/modules](https://carc.unm.edu/docs/running-jobs/modules/),
[software/cuda-aware-mpi](https://carc.unm.edu/docs/software/cuda-aware-mpi/),
[about/partners](https://carc.unm.edu/docs/about/partners/).

## Active clusters

| Cluster | Nodes | CPU cores | GPUs | Interconnect (docs wording) | RAM | Notes |
|---|---:|---:|---|---|---|---|
| **Easley** | 65 | 4,160 (64/node) | 36× NVIDIA L40S + 8× NVIDIA H100 | "NVIDIA NDR 800 Gbps InfiniBand core network" | 23.3 TB total | newest; Easley-local 720 TB all-flash GPFS scratch |
| **Hopper** | 61 | 2,176 | 37× NVIDIA A100 (+ V100 in condo/lab partitions) | "NVIDIA HDR 400 Gbps InfiniBand network" | not documented | Dell PowerEdge R640/R740, Xeon Gold 6226R / 6242 (Cascade Lake), 32 cores/node, 448 GB local disk, Rocky Linux (legacy table); hosts the 2 PB BeeGFS |

Interconnect: the [Easley launch news](https://carc.unm.edu/news--events/News/easley-cluster.html)
resolves the docs' "800 Gbps": "Easley's core network is based on NVIDIA's 800 Gbps
InfiniBand, with **200 Gbps connectivity to the nodes**" — i.e. NDR200 (2x) HCAs at the
nodes and an 800 Gbps-class (2× NDR400 per OSFP cage) core. Easley is Dell hardware; the
all-flash filesystem is 768 TB raw (720 TB in the docs). Hopper's "HDR 400 Gbps" is still
ambiguous (HDR ports are 200 Gb/s): `ibstat` on a Hopper node settles it (`TODO(carc)`).
The news also states Easley brought "a fivefold reduction in the number of racks and physical
CPUs" relative to Wheeler at 7–10× the performance — a density datum for Topic 04.

### Easley node map (from `sinfo`, 2026-07-25)

| Partition | Nodes | Count | Per node | Notes |
|---|---|---:|---|---|
| general (default) | easley[001-048] | 48 | 64 cores, CPU only; ~3.7 GB/CPU default memory | 2-day limit, 8 h default |
| bigmem | easley[049-050] | 2 | ~2 TB RAM | |
| h100 | easley[051-054] | 4 | 2× NVIDIA H100 | group-gated (ColdFront) |
| l40s | easley[055-057] (+ easley[058-063] reserved, visible in `scavenger`) | 3 + 6 = 9 | 4× NVIDIA L40S | group-gated; 9 × 4 = 36 L40S |
| interactive / debug / scavenger | overlapping sets | | | 4 h / 1 h / preemptible |
| liulab | lab nodes | | | 7-day limit |

The documented 65 nodes vs. 63 in `sinfo` (`easley001`–`easley063`) leaves two nodes
unaccounted for (`TODO(carc)`). Easley's CPU vendor and model are not in the docs
(`TODO(carc)`: `lscpu`); `--ntasks-per-node` must be ≤ 64.

GPU types matter for Topic 02: the **L40S has no NVLink**, so tensor parallelism on an
L40S node crosses PCIe only; the two H100s per node may or may not have an NVLink bridge
(`TODO(carc)`: `nvidia-smi topo -m`).

### Hopper partitions

| Partition | Notes |
|---|---|
| general (default) | 10 community CPU nodes; `DefMemPerCPU=2938` (~2.9 GB/CPU); 2-day limit |
| debug | 2 nodes; 4 h |
| condo | group-restricted mixed CPU/GPU (A100, V100) nodes; 2 days |
| bugs, pcnc, pathogen, tc, gold, fishgen, neuro-hsc, pna, geodef, insar | lab-restricted; 7 days |
| cup-ecs, tid, biocomp, chakra | lab-restricted, GPU (A100/V100); 7 days |
| quark, toadpole | lab-restricted, GPU (A100); 10 days |

GPUs per node, the number of GPU nodes, the V100 count, and node-level memory are not
documented (`TODO(carc)`). Hopper [launched as a condo cluster](https://carc.unm.edu/news--events/News/carc-launches-hopper.html)
with 53 nodes, 1,760 Intel Xeon Gold cores and 8.2 TB of RAM, with OVPR-funded community
nodes plus researcher-purchased nodes (Melanie Moses is named as one purchaser), and has
since grown to 61 nodes / 2,176 cores.

## Retired clusters (legacy reference — useful as the historical series for H1.5)

| Cluster | Node model | CPU | Nodes | Cores/node | GPU | Fabric | Notes |
|---|---|---|---:|---:|---|---|---|
| Wheeler | SGI Altix XE | Xeon X5550 2.67 GHz (Nehalem-EP) | 304 | 8 | — | QDR, Mellanox IS5600 InfiniScale IV, ConnectX-2 (MT26428) | diskless, 6 GB/core, CentOS 7 |
| Gibbs | Dell PowerEdge R620 | Xeon E5-2670 2.6 GHz (Sandy Bridge) | 24 | 16 | — | QDR | 4 GB/core |
| Xena | Dell PowerEdge R730 / R930 | Xeon E5-2640 (v3, Haswell) 2.6 GHz; E7-4809 (v3) 2.0 GHz bigmem | 32 | 16 / 32 | Tesla K40M: 24 single-GPU + 4 dual-GPU nodes | FDR (56 Gb/s) | bigmem 1 TB ×2, 3 TB ×2; the [infrastructure page](https://carc.unm.edu/systems/carc-infrastructure.html) says 720 cores vs 576 in the legacy table |
| Taos | Dell PowerEdge R630 | Xeon E5-2698 v4 2.20 GHz (Broadwell) | 9 | variable | — | FDR, Mellanox SX6000, ConnectX-3 (MT4099) | |

## Storage

| Tier | System | Capacity | Where | Network |
|---|---|---|---|---|
| Easley-local scratch (`/easley/scratch`) | IBM Storage Scale (GPFS), all-flash | 720 TB | Easley only | `TODO(carc)` (IB or Ethernet) |
| Center-wide scratch (`/carc/scratch`) | BeeGFS | 2 PB | both clusters; physically hosted on Hopper | `TODO(carc)` |
| Home + project (`/users`, `/projects`) | NetApp enterprise, hourly→monthly snapshots (4 months) | 2.4 PB | all machines | `TODO(carc)` |
| Node-local | `/tmp`, `/dev/shm` | Hopper 448 GB/node; Easley `TODO(carc)` | | |

## Facility (Topic 04)

- "dedicated 1,200 square-foot research data center"
- "270 kVA of UPS capacity"
- **90 tons of dedicated cooling** across three Liebert AC systems (≈ 317 kW of heat
  removal, consistent with the 270 kVA UPS) — per Tyson Swetnam, CARC Director, 2026-09-08.
  The facilities page says "990 tons"; that is a documentation error to be fixed upstream.
- Campus: "multiple 10 Gbps links, including a dedicated 10 Gbps connection to UNM's
  Science DMZ"; external: "100 Gbps connections to ESnet and the Western Regional Network
  through the Albuquerque Gigapop".
- perfSONAR node at http://perfsonar.alliance.unm.edu (usable for the WAN-boundary measurements).
- PUE, IT load, PDU/BMS metering, cooling type per row, rack density: `TODO(carc)` (not published).

## Software environment (for `benchmarks/slurm/site.env`)

- Scheduler: Slurm with fairshare; GPU requests `--gres=gpu:N`; typed gres names `TODO(carc)`.
- Modules (Lmod): `gcc/14.2.0-j33x`, `openmpi/4.1.7-762w`, `miniconda3/latest`,
  `intel-oneapi-*`; a CUDA-aware OpenMPI build ships with a matching UCX
  (`software/cuda-aware-mpi`); `module avail singularity` for containers.
- Interactive: JupyterHub (hopper.alliance.unm.edu, easley.alliance.unm.edu/jupyter), Open
  OnDemand, ColdFront allocations, XDMoD usage metrics (a possible source of historical
  utilization for Topic 04).

## Partner infrastructure

ACCESS-CI, **Jetstream2** (see [05-jetstream2-inventory.md](05-jetstream2-inventory.md)),
CyVerse, and MESA (NSF NAIRR). CARC is also "expanding into on-premises cloud (OpenStack),
container orchestration (Kubernetes), and data management (iRODS)".

## Still needed from the clusters (Phase 1 checklist)

1. `lscpu` on easley001, easley049, easley051, easley055, and one Hopper node of each type → CPU model, sockets.
2. `nvidia-smi -q` / `nvidia-smi topo -m` on easley051 and easley055 and a Hopper A100 node → H100 PCIe vs SXM, NVLink bridges, PCIe gen/width, GPUs per Hopper node.
3. `ibstat` / `ib_sysfs.txt` on one node per type → HCA model and port count (Easley expected NDR200; Hopper HDR ports).
4. `ibnetdiscover` (umad access) or `scontrol show topology` → leaf/spine layout, hosts per leaf, uplinks, oversubscription.
5. `ethtool` → management/campus NIC speeds; UNM IT → exact campus uplink count.
6. Facilities → cooling tonnage, PDU/UPS metering, chilled-water data, floor plan.
