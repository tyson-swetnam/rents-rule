# Topic 02 — Communication locality under load (inference workloads)

## The question as asked

> Software question, first focusing on inference loads: How much communication is there
> over the wires at each scale (i.e., between compute nodes, between servers, between
> racks, etc.) under load? How much does this vary? — Melanie

> A fat-tree network will have a Rent's p=1 but a p < 1 is how far down a workload can be
> pushed — and I don't think anyone has ever measured anything like this. — Tyson

## Sharpened statement

Hardware Rent's rule (Topic 01) is about *installed* capacity. This topic is about *used*
capacity. For a workload `W` running on module `M`, define

- `B_ℓ(M)` — bytes crossing the boundary of `M` per unit of work (per generated token for
  inference; per training step; per request), measured with counters at each level:
  NVLink/PCIe (GPU boundary), InfiniBand/Ethernet NIC (node boundary), switch uplinks
  (rack/pod boundary), campus uplink (facility boundary).
- **Workload Rent exponent** `p_w`: slope of `log B_ℓ` vs `log G(M)` across levels.
- **Workload locality step** `λ_w,ℓ = B_ℓ(M) / Σ_children B(c)`.

Tyson's remark becomes a precise comparison: `p_w` (or `λ_w`) against `p_hw` (or
`λ_hw`) level by level. Where `λ_w < λ_hw` the fabric has slack; where `λ_w > λ_hw` the
boundary is the bottleneck and the workload cannot be "pushed further down".

## Predictions from the structure of transformer inference

Tensor parallelism (TP) inside a node and pipeline parallelism (PP) across nodes move very
different amounts of data. For a decoder layer with hidden size `h`, `L` layers, TP degree
`n`, activations in 2-byte formats, and ring all-reduce:

- **TP (NVLink, inside node):** two all-reduces per layer per token, each moving
  `2(n−1)/n · h · 2 B` per GPU → `B_gpu ≈ 2L · 2(n−1)/n · 2h` bytes/token/GPU.
  Llama-70B-class (`L=80, h=8192, n=8`): ≈ **4.6 MB per token per GPU** over NVLink.
- **PP (InfiniBand, across nodes):** one activation vector per stage boundary per token,
  `h · 2 B` ≈ **16 KB per token** per boundary.

So the predicted node-boundary locality step for TP-inside/PP-across serving is
`λ_w ≈ 16 KB / (8 × 4.6 MB) ≈ 4 × 10⁻⁴` — two orders of magnitude *below* the hardware step
`λ_hw ≈ 0.03–0.1` from Topic 01. Inference is designed to be extremely local; the
interesting measurements are (a) whether the counters confirm these numbers, (b) how
KV-cache transfer, prefill/decode disaggregation, and batching change them, and (c) what
happens when a model no longer fits a node (TP across nodes), which flips `λ_w` toward 1.

## Hypotheses

- **H2.1** Bytes/token at each level are nearly deterministic for a fixed
  (model, TP, PP, batch) configuration and match the formulas above within 20 %.
- **H2.2** `λ_w,node ≪ λ_hw,node` for single-node models; `λ_w,node → 1` when TP spans nodes.
  The crossover model size is a property of the hardware step `λ_hw`.
- **H2.3** Variance in *bytes per second* (not per token) is dominated by request arrival
  and length statistics, which is Topic 03's domain (heavy-tailed prompt/output lengths
  ⇒ long-range dependence).
- **H2.4** Data-parallel training (all-reduce of gradients every step) has `λ_w,node` orders
  of magnitude larger than inference; measuring both bounds the range CARC's fabric must serve.
- **H2.5** Storage traffic (checkpoint loads, dataset reads from Lustre/NFS) crosses the
  rack and facility boundaries and may dominate `B` at those levels for real jobs.

## What CARC can measure

1. Serve a model with vLLM (or SGLang / TensorRT-LLM) under Slurm:
   `benchmarks/inference/run_vllm_server.sh` — TP within a node, optional PP across nodes.
2. Drive it with `benchmarks/inference/load_generator.py` (Poisson arrivals, configurable
   prompt/output length distributions incl. Pareto tails, records tokens and latency).
3. Sample counters at 100 ms on every node in the job: `telemetry/collectors/collect_all.sh`
   (DCGM NVLink/PCIe bytes, IB port counters, NIC counters, power).
4. Normalize: `rentscale.counters` turns cumulative counters into rates; join with the load
   generator's token log to get bytes per token per level; `rentscale.rent.fit_rent` for `p_w`.
5. Sweep: TP ∈ {1,2,4,8}, PP ∈ {1,2,4}, batch, request rate; model sizes that do / do not
   fit one node. Template: `benchmarks/slurm/inference_tp_pp.sbatch`.
6. Contrast: NCCL all-reduce scaling (`benchmarks/slurm/nccl_scaling.sbatch`) as the
   training-like upper bound.

Rack- and pod-level counters need switch access (`telemetry/collectors/switch_counters.sh`,
`perfquery` or SNMP) — coordinate with CARC operations.

## Site specifics (2026-09)

- CARC Easley's **L40S nodes have no NVLink**: TP across 4 L40S runs over PCIe Gen4, so the
  die-boundary bytes/token of H2.1 cross PCIe rather than NVLink — a built-in contrast with
  the 2× H100 nodes (NVLink bridge `TODO(carc)`) and with Jetstream2's SXM A100/H100 nodes.
- Jetstream2 runs a public **vLLM inference service** (Llama 4 Scout and gpt-oss-120b on 2× H100
  each, muse-glimmer on 1× H100, stated 83–180 tokens/s): a documented TP = 2 deployment to
  compare with our counters; Jetstream2 g5.2xl / g5.4xl flavors reproduce it under our control.
- Easley GPU partitions (`h100`, `l40s`) are group-gated through ColdFront; 2-day walltime.

## What Moses et al. (2016) adds

- **Steady state is the roofline ridge.** The model assumes delivery matches processing
  (`T_net = T_node`, the network always full). For inference that is the balance between
  bytes/token ÷ link bandwidth and compute time per token at the binding level. **H2.6:**
  measure both and report `T_net/T_node` per level; the level with the ratio nearest 1 is the
  bottleneck, as the paper found the wire (not the transistor) limits chip throughput.
- **Rent's communication probability.** Bezerra et al. (2010) derive from Rent's rule the
  probability that a message travels a given hierarchical distance; in our units the
  fraction of a node's traffic crossing the level-`ℓ` boundary is `k^{−ℓ(1−p_w)}`. Fitting
  that curve to the per-level bytes/token gives `p_w` in one step (`rent.p_from_locality_step`).
- **Locality is the computer's advantage.** The paper singles out communication locality as
  the lever multicellular organisms lack; TP-inside/PP-across serving is that lever applied
  deliberately, and `λ_w ≪ λ_hw` (H2.2) is the measurement of how hard it is pulled.

## What must come from elsewhere

Production inference telemetry from hyperscalers (rack-level and pod-level bytes per token
across a fleet). Our per-token normalization makes CARC numbers comparable with theirs.

## Literature

- Heirman, Dambre, Stroobandt & Van Campenhout 2008, *Rent's rule and parallel programs:
  characterizing network traffic behavior* (SLIP) — the closest prior "workload Rent exponent" (`verify`).
- Shoeybi et al. 2019 (Megatron-LM); Narayanan et al. 2021 (3D parallelism, communication volumes).
- Pope et al. 2023, *Efficiently scaling transformer inference* (TP communication analysis).
- Benson, Akella & Maltz 2010, *Network traffic characteristics of data centers in the wild*;
  Kandula et al. 2009; Roy et al. 2015 (Facebook) — measured intra-rack vs inter-rack locality.
