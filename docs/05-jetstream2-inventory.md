# Jetstream2 inventory

Jetstream2 is the NSF "always-on" research cloud (NSF award 2005506), primary cloud at
Indiana University with regional clouds at Arizona State, Cornell, the University of
Hawaiʻi, and TACC; Dell is the primary supplier; reachable through ACCESS allocations
(listed on CARC's [partners page](https://carc.unm.edu/docs/about/partners/)). All numbers
below are from https://docs.jetstream-cloud.org —
[overview/config](https://docs.jetstream-cloud.org/overview/config/),
[overview/network](https://docs.jetstream-cloud.org/overview/network/),
[general/instance-flavors](https://docs.jetstream-cloud.org/general/instance-flavors/),
[faq/gpu](https://docs.jetstream-cloud.org/faq/gpu/),
[inference-service/overview](https://docs.jetstream-cloud.org/inference-service/overview/) —
and describe the **primary cloud**; the network page notes "regional sites may be
configured differently". Encoded in `hardware/reference/hierarchy_template.yaml` (group
`jetstream2`) and `data/reference/jetstream2_flavors.csv`.

## Why it matters for this project

It is a documented, homogeneous, **Ethernet Clos** fabric (against CARC's InfiniBand
fat-trees), with published switch models and port counts, three GPU generations on one
network, GPUs sold in fractions (vGPU) as well as whole nodes, and a public **vLLM inference
service** whose hardware is stated. It is the second facility in the returns-to-scale table
and the natural place to repeat Phase 3 (inference locality) inside a VM.

## Node types (primary cloud)

| Type | Count | Model | CPUs | Cores | RAM | GPUs | Local disk | Network |
|---|---:|---|---|---:|---|---|---|---|
| Compute | 384 | Dell PowerEdge C6525 | 2× AMD EPYC 7713 (Milan) | 128 | 512 GiB | — | 240 GB SSD | 1× 100 GbE |
| Large memory | 32 | Dell PowerEdge R7525 | 2× AMD EPYC 7713 | 128 | 1,024 GiB | — | 480 GB SSD | 1× 100 GbE |
| A100 GPU | 90 | Dell PowerEdge XE8545 | 2× AMD EPYC 7713 | 128 | 512 GiB | 4× A100 SXM4 40 GB | 960 GB SSD | 2× 100 GbE |
| H100 GPU | 24 | Dell PowerEdge XE9640 | 2× Intel Xeon Platinum 8468 | 96 | ~1,007 GiB | 4× H100 SXM 80 GB | 500 GB NVMe | 2× 100 GbE |
| L40S GPU | 8 | Dell PowerEdge R760XA | 2× Intel Xeon Gold 6438M | 64 | ~503 GiB | 4× L40S 48 GB | 500 GB NVMe | 2× 100 GbE |

Totals: 538 nodes, 67,584 cores, 488 GPUs (360 A100 + 96 H100 + 32 L40S), ≈ 296 TiB RAM,
14 PB Ceph (the overview page says "17.2 petabytes" and "8 petaFLOPS" system-wide; both
figures recorded). The config page phrases per-node networking as "100 Gbps x4 to
Internet2, 100 Gbps to switch"; the network page gives single 100 GbE for CPU and
large-memory hosts and dual 100 GbE for GPU hosts (as of October 2024). Ubuntu on all nodes.

## Network (primary cloud)

- Two-tier spine-and-leaf, fat-tree/Clos, **no inter-switch links**; Cumulus Linux, BGP,
  RFC 1918 loopbacks.
- Spines: **6× Mellanox SN4600** (64× 100 GbE each). Leaves: **37× Mellanox SN2700**
  (32× 100 GbE each). Control-plane and storage nodes dual 100 GbE.
- Uplinks: "2x100 Gbps uplinks from the cloud infrastructure to the data center
  infrastructure"; "100 Gbps connectivity from the site infrastructure to the Internet2
  backbone"; "100 Gbps connectivity to the ACCESS research network via virtualized link".
- **Inferred, not documented:** with one link per spine per leaf (37 ≤ 64 spine ports), a
  leaf has 6 uplinks and 26 downlinks → **4.3:1 oversubscription** at the leaf, i.e. a
  hardware Rent exponent well below 1 above the node. Two links per spine per leaf is
  impossible (74 > 64 ports), so the range is 6–10 uplinks per leaf (`TODO(js2)`: ask
  Jetstream2 operations, or read `lldp`/port counts if they will share them).

## GPUs as modules smaller than a die

Flavors g3.medium / g3.large are **25 % / 50 % of an A100** via NVIDIA vGPU (no CUDA
debugging or unified memory); g3.xl / g4.xl / g5.xl are whole A100 / L40S / H100; 2- and
4-card flavors (g4.2xl, g4.4xl, g5.2xl, g5.4xl) "launch on a single node" and are granted
on request. Whether NVLink is exposed inside a multi-GPU VM is not stated (`TODO(js2)`:
`nvidia-smi topo -m` inside a g5.2xl). Full flavor table: `data/reference/jetstream2_flavors.csv`.

## Inference service (Topic 02 reference point)

Three vLLM servers on Jetstream2 instances, OpenAI-compatible API, free with an ACCESS
account (as of 2025-05-30): Llama 4 Scout on 2× H100 (up to 83 tokens/s), gpt-oss-120b on
2× H100 (up to 180 tokens/s), muse-glimmer (30B, FP16) on 1× H100. Chat UI at
https://llm.jetstream-cloud.org. These are exactly the TP = 1–2 configurations of Phase 3;
our own g5.2xl/g5.4xl runs can reproduce them with counters.

## What can and cannot be measured from inside a VM

| Level | Measurable from a Jetstream2 instance | How |
|---|---|---|
| die / GPU↔GPU | yes, if the flavor has ≥ 2 GPUs | `nvidia-smi nvlink -gt d`, DCGM if installable |
| node NIC | yes (virtio / SR-IOV NIC counters) | `nic_counters.py`; note virtual NIC ≠ host 100 GbE |
| leaf / spine | no (operator only) | ask for SNMP `ifHCInOctets` on leaf uplinks, or infer from `iperf3` between instances on different hosts |
| site uplinks | partly | `iperf3`/perfSONAR to CARC across Internet2 (both ends have perfSONAR: perfsonar.alliance.unm.edu) |

Allocation cost: g5.xl = 128 SU/h, g5.4xl = 512 SU/h; m3.3xl (whole compute node) = 128 SU/h.
