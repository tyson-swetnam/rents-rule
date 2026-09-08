# rents-rule — scaling theory of modern computing

Does Rent's rule hold for data centers? This project asks how **compute** (transistors),
**communication** (wires, ports, bandwidth, and the traffic that actually crosses them),
**power**, and **cooling** scale with system size across the hierarchy

```
die → package → node → rack → pod / row → facility → WAN
```

and whether the returns to scale at each level are increasing, linear, or diminishing —
the same question metabolic scaling theory (MST) asks of organisms. It grew out of an
August 2026 exchange between Melanie Moses (UNM CS / Biology), Tyson Swetnam (Director,
UNM Center for Advanced Research Computing, CARC), and Matthew Fricke; see
[docs/00-origin-email-thread.md](docs/00-origin-email-thread.md).

Nobody appears to have measured a Rent exponent for a data center hierarchy — neither a
*hardware* exponent (installed wires or bandwidth vs. transistors per module) nor a
*workload* exponent (bytes that actually cross each module boundary under load). CARC's
clusters are a place where both can be measured end to end. This repository is the plan,
the instruments, and the analysis code to do that.

## The questions (from the email thread)

1. **Hardware Rent's rule.** At each level (GPU/CPU, server, rack, pod, data center),
   what is the ratio of external communication paths to transistors inside the module?
   If a GPU has 10¹⁰ transistors and 10³ wires out, does a rack with 10¹² transistors
   have 10⁵ wires out? What is the exponent `p` in `T = t·G^p`?
2. **Communication under load.** For inference workloads, how many bytes cross each
   boundary (GPU↔GPU, node↔node, rack↔rack, facility↔WAN) per unit of work, and how much
   does that vary? This is the *workload* Rent exponent and a direct measure of locality.
3. **Wires vs. bandwidth.** Transistors and wires do not scale one-to-one within a server
   (a DGX has many GPUs per external link). Bandwidth, not wire count, is what operators
   measure. Which definition of `T` gives a stable exponent?
4. **Time-domain self-similarity.** Ethernet traffic is classically 1/f with Hurst
   exponents `H ≈ 0.7–0.9` (Leland et al. 1994). Is `H` preserved across aggregation
   levels of the data center hierarchy, and how does it relate to spatial locality?
5. **Power and cooling networks.** PUE improves with size and age of the facility
   (~1.1–1.2 new hyperscale vs ~1.5–1.6 legacy), but heat flux per rack is rising fast.
   How do the power-delivery and cooling networks scale, and where do returns diminish?
6. **Returns to scale.** Traditionally compute has increasing returns (Moore, Dennard),
   Rent's rule offers linear communication cost when locality is fixed, and cooling/power
   face diminishing returns. Can we put numbers on each term for a real facility?

Each question has a working folder under [`topics/`](topics/README.md).

## Repository map

| Path | What it holds |
|---|---|
| [`topics/`](topics/README.md) | One folder per research question: sharpened statement, hypotheses, what CARC can measure, literature, links to scripts. |
| [`docs/`](docs/) | Origin email, research questions, measurement plan for CARC (+ Jetstream2 addendum), CARC and Jetstream2 inventories from their documentation, background primers, references, glossary. |
| [`hardware/`](hardware/README.md) | Static census: node/fabric inventory scripts, reference tables (transistor counts, link bandwidths), hierarchy template, Rent census tool. |
| [`benchmarks/`](benchmarks/README.md) | Active experiments: intra-node (NVLink/PCIe), inter-node (InfiniBand/MPI), inference load, and Slurm job templates. |
| [`telemetry/`](telemetry/README.md) | Passive collectors for IB/NIC/NVLink/PCIe/power counters, designed to run beside a job. |
| [`src/rentscale/`](src/rentscale/) | Python package: Rent fits, topology generators (fat-tree, tapered tree, mesh), Hurst/spectral estimators, counter → rate conversion, benchmark output parsers, allometric/PUE models, census resolver, CLI. |
| [`tests/`](tests/) | pytest suite on synthetic data with known answers (fat-tree ⇒ p=1, d-mesh ⇒ p=1−1/d, fGn with known H, …). |
| [`data/`](data/README.md) | `reference/` curated public tables (PUE by facility, …); `raw/` and `processed/` are gitignored measurement outputs. |
| [`notebooks/`](notebooks/) | Analysis notebooks (empty until there is data). |

## Quick start (laptop, no hardware)

```bash
cd rents-rule
make venv          # uv or pip; creates .venv with the package installed editable
make test          # ~30 s: synthetic fat-tree, mesh, fGn, parsers
make demo          # prints Rent exponents for synthetic topologies and H for synthetic traffic
```

Or with conda: `conda env create -f environment.yml && conda activate rents-rule`.

## Running on CARC

The measurement campaign is laid out phase by phase in
[docs/02-measurement-plan.md](docs/02-measurement-plan.md). In short:

```bash
# Phase 1 — static census (login node + one srun per node type; no user impact)
bash hardware/inventory/slurm_inventory.sh  runs/census
srun -N1 -p <partition> bash hardware/inventory/inventory_node.sh runs/census
bash hardware/inventory/fabric_discover.sh   runs/census     # needs umad access
python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml

# Phase 2 — delivered bandwidth vs module size (exclusive nodes)
bash benchmarks/slurm/submit_scaling_sweep.sh 1 2 4 8 16

# Phase 3 — inference locality (vLLM TP/PP sweep with counters)
sbatch benchmarks/slurm/inference_tp_pp.sbatch

# Phase 4 — passive traffic time series for Hurst analysis
sbatch benchmarks/slurm/traffic_capture_passive.sbatch
```

Every script degrades gracefully when a tool (`nvidia-smi`, `ibstat`, `dcgmi`, …) is
absent, records what it could not collect, and never captures packet payloads — only
byte and packet counters.

## Status

- 2026-09-08 — project scaffold, topic dossiers, analysis package and tests created.
  Nothing has been measured yet. Reference tables carry a `confidence` column; values
  marked `verify` were entered from memory and must be checked against vendor sources
  before publication.
- 2026-09-08 — CARC (Easley, Hopper, retired Wheeler/Gibbs/Xena/Taos, facility) and
  Jetstream2 (primary cloud, Clos fabric, flavors, inference service) specifications
  transcribed from their documentation sites into `docs/03`, `docs/05`,
  `hardware/reference/hierarchy_template.yaml` (groups `carc`, `jetstream2`), and
  `data/reference/`. Remaining `TODO(carc)` items (CPU models, per-HCA rates, GPUs per
  Hopper node, fabric layout, PUE) need the inventory scripts or UNM facilities.

## People

- Melanie Moses — UNM Computer Science & Biology (scaling theory, MST for data centers)
- Tyson L. Swetnam — UNM CARC Director, Computer Science (measurement, infrastructure)
- Matthew Fricke — UNM Computer Science

Related prior work by the group: Moses, Bezerra, Edwards, Brown & Forrest (2016),
*Energy and time determine scaling in biological and computer designs*, Phil. Trans. R.
Soc. B 371:20150446. Tyson's fractal/MST notebooks: https://tyson-swetnam.github.io/fractal-notebooks/
