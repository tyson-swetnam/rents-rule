# Research questions and definitions

This is the canonical statement of what the project measures. Topic dossiers under
[`topics/`](../topics/README.md) expand each question; this file fixes the vocabulary so
that numbers from CARC, from other centers, and from the literature are comparable.

## Definitions

**Hierarchy levels** (ordered, small → large):

| ℓ | level | example module | what is "inside" |
|---|---|---|---|
| 0 | die | one GPU die, one CPU CCD/tile | transistors of that die |
| 1 | package | GPU board incl. HBM; CPU socket | dies + memory |
| 2 | node | server / DGX / blade | CPUs, GPUs, NICs, local storage |
| 3 | rack | 42U rack | nodes + (often) leaf switch |
| 4 | pod / row / scalable unit | leaf-spine group | racks + leaf + spine switches |
| 5 | facility | the data hall / center | pods + core + storage |
| 6 | WAN | campus, Internet2, cloud | facilities |

**Module `M`** — any subtree of the hierarchy. **Gates `G(M)`** — transistors inside `M`
(convention: sum of published transistor counts of CPUs, GPUs, and any NIC/switch ASICs
with published counts; unknown parts are listed, not guessed). Where transistor counts are
unavailable, secondary size measures are recorded alongside: cores, peak FLOP/s, memory
bytes, IT watts.

**Terminals `T(M)`** — external communication capacity, always reported in three forms:

- `T_lanes` — high-speed differential pairs (per direction) crossing the boundary;
- `T_ports` — physical ports / cables crossing the boundary;
- `T_gbps` — aggregate line rate crossing the boundary, Gb/s per direction.

**Rent's rule** — `T = t · G^p`. `p` is the Rent exponent, `t` the Rent coefficient.

**Hardware Rent exponent `p_hw`** — from installed capacity (census).
**Workload Rent exponent `p_w`** — from *used* capacity: bytes crossing the boundary of
`M` per unit of work (`B(M)`), fitted as `B = b · G^{p_w}`.

**Locality step `λ_ℓ`** — at the boundary between level ℓ−1 and ℓ,
`λ_ℓ = T(M_ℓ) / Σ_{children} T(c)` (hardware) or the same with `B` (workload). It is the
fraction of the children's external capacity (traffic) that leaves the parent. `λ = 1`
means no locality is exploited at that level.

**Effective dimension** — `d_eff = 1 / (1 − p)`, from the Ozaktas bound `p ≤ 1 − 1/d`.

**Model dimensions (Moses et al. 2016)** — `D_l` (layout dimension: lengths grow as
`λ^{i/D_l}` per level), `D_r` (thickness/bandwidth: `λ^{i/D_r}`; 2 = area preserving), `D_w`
(communication: links per module grow as `λ^{i/D_w}`; Rent's `p = 1/D_w`). The
network-energy sum converges iff `D_w ≥ D_l/(D_l − 1)`, i.e. `p ≤ 1 − 1/D_l`. See
[background/energy-time-minimization.md](background/energy-time-minimization.md).

**Hurst exponent `H`** — long-range dependence of a traffic rate series `X(t)`;
`Var(X^{(m)}) ∝ m^{2H−2}` for block means over `m` samples; `H = 0.5` is memoryless.
**Spectral slope `β`** — `S(f) ∝ f^{−β}`, `β = 2H − 1` for fractional Gaussian noise.

**PUE** — facility energy / IT energy over a period (ISO/IEC 30134-2).

## The questions

### Q1 — Hardware Rent's rule (Topic 01)
1. What are `p_hw` (each of the three `T` definitions) and `λ_ℓ` at each level of CARC's clusters?
2. How does the profile differ between GPU and CPU-only clusters?
3. Across GPU generations at fixed level, do lanes and bandwidth scale with transistors with different exponents?
4. Which `T` definition gives the most stable `p` across levels (Tyson's "wires ≠ bandwidth")?

### Q2 — Communication locality under load (Topic 02)
1. For inference (TP inside node, PP across), what are bytes/token at GPU, node, rack, and facility boundaries?
2. What is `p_w`, and how does `λ_w,ℓ` compare with `λ_hw,ℓ`? Where is the slack, where the bottleneck?
3. How much do bytes/token vary with batch, request rate, model size, and serving stack features (KV transfer, disaggregation)?
4. How does inference compare with training (all-reduce) and with storage traffic?

### Q3 — Temporal self-similarity (Topic 03)
1. What is `H` for port-level traffic under production load and under controlled inference load?
2. Is `H` preserved under spatial aggregation (port → leaf → spine → uplink)?
3. Does injecting heavy-tailed request lengths (tail index `α`) produce `H = (3 − α)/2`?

### Q4 — Power and cooling networks (Topic 04)
1. PUE vs facility size and vintage from public data; CARC's own PUE.
2. How do node power and work scale (`P ∝ W^α`) on CARC hardware?
3. How do power-delivery and cooling distribution networks scale with size (levels, lengths, losses)?

### Q5 — Returns to scale (Topic 05)
1. For each cost term, what is the exponent `γ` and its regime (increasing / linear / diminishing)?
2. Under Rent's rule, does communication infrastructure scale linearly (`p_hw < 1`) or as `N log N` (`p_hw = 1`) at CARC and at hyperscale?
3. Does a size optimum exist, and where?
4. Which regime are data centers in: the chip regime of Moses et al. (2016), where nodes shrink and
   power scales as `N^{1/2}`, or the fixed-node regime where linear is the ceiling and only locality
   (`p ≤ 1 − 1/D_l`) prevents sub-linear returns? (H-ET1, H-ET2 in the primer.)

### Q6 — Dimensionality (Topic 06)
1. What is the profile of `d_eff` across levels?
2. What does the "five-dimensional" argument predict once restated as a Rent inequality, and can any of it be tested with the above?

## Deliverables

1. **Rent census of CARC** — table of `(level, module, G, T_lanes, T_ports, T_gbps)` with fits and `λ` profile.
2. **Bandwidth-scaling benchmark set** — reusable Slurm jobs and parsers; delivered bisection bandwidth vs module size.
3. **Inference locality dataset** — bytes/token per boundary over a TP/PP/batch sweep, with counters and load logs.
4. **Traffic time-series archive** — port-level counters at 100 ms over days, with `H` and `β` per port and aggregate.
5. **Power dataset** — node power under the benchmarks; partial facility PUE if the building management system allows.
6. **Synthesis** — returns-to-scale table and `d_eff` profile; a paper draft with Melanie's group.
