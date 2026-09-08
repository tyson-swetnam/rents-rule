# The energy–time minimization model (Moses et al. 2016) and the data-center regime

Moses, Bezerra, Edwards, Brown & Forrest (2016), *Energy and time determine scaling in
biological and computer designs*, Phil. Trans. R. Soc. B 371:20150446
([PMC4958940](https://pmc.ncbi.nlm.nih.gov/articles/PMC4958940/), PMID 27431524). This is
the theoretical spine of the project: it is Melanie's own model, it already contains
Rent's rule as one of its three dimensions, and its "chips" regime is exactly the regime
whose end (Moore, Dennard) motivates her data-center question. Implemented in
`src/rentscale/energytime.py`; the summary table below is what `rentscale demo` prints.

## The model in one page

A hierarchical delivery network with branching factor `λ`, `H` levels and `N = λ^H`
terminal nodes (capillaries; transistors; for us GPUs or servers). Level 0 is the smallest.
Three scaling dimensions describe how the network grows with level `i`:

| equation | meaning | biology | chips | data center (ours) |
|---|---|---|---|---|
| `l_i = l_0 λ^{i/D_l}` (2.1) | length of a pipe/wire at level `i`; `D_l` is the spatial dimension the nodes fill | `D_l = 3` | `D_l = 2` | 2 (a hall floor) to 3 (a rack, a 3-D package); fat-trees escape any finite `D_l` |
| `r_i = r_0 λ^{i/D_r}` (2.2) | thickness (pipe radius, wire width): `D_r = 2` is area-preserving branching (flow conserved) | optimum `24/11 ≈ 2.18` (blood must slow) | 2 (Dennard) | link **bandwidth** growth up the hierarchy: full bisection ≙ area preserving; oversubscription ≙ `D_r > 2` |
| `w_i = w_0 λ^{i/D_w}` (2.3) | links per module at level `i`; **Rent's rule with `p = 1/D_w`** | `w_i = 1` (a single tree) | `D_w = 2`, `p = 1/2` | `p_hw` from the census, `p_w` from traffic |

Energy `E_sys = E_net + E_node` (network + nodes) and time `T_sys` (delivery or processing,
whichever is slower) are minimized jointly: the *energy–time product*, the computer
architect's energy–delay product. Assumptions: steady state (supply matches demand, the
network is always full — "pipelining"); nodes are service volumes with fixed processing
rate; in chips the total area is fixed so `l_0, r_0 ∝ N^{−1/D_l}` as transistors shrink.

### What it predicts and how it tested

- **Mammals.** With area-preserving branching and no blood slowing (`D_r = 2`) the model
  recovers Kleiber's 3/4; letting blood slow (`D_r > 2`) and adding node energy produces the
  *curvature* seen in Kolokotrones et al.'s data. The energy–time optimum that keeps
  `T_node` invariant is `D_r = 24/11`; it fits slightly better (m.s.e. 0.0271) than the
  extended WBE model (0.0287); the best statistical fit is `D_r = 2.50`.
- **Chips.** Network energy is proportional to total wire length,
  `E_net ∝ Σ_i l_i w_i n_i ∝ N^{1−1/D_l} Σ_i λ^{i(1/D_l + 1/D_w − 1)}` (3.9–3.10). The sum
  converges when `D_w ≥ D_l/(D_l − 1)`, i.e. **`p ≤ 1 − 1/D_l`** — the same bound Ozaktas
  derived for embeddability. Then `E_net ∝ N^{1/2}`, `E_node ∝ N^{1/2}`, wire delay
  `T_net ∝ N^0` (needs `D_r = 2`), transistor delay `T_node ∝ N^{−1/2}`. Optimum:
  `D_l = D_r = D_w = 2`, which *is* Dennard scaling with Rent's `p = 1/2`.
  Predictions: **power `P ∝ N^{1/2}`** (measured exponent 0.495, 95 % CI 0.46–0.53, 523
  microprocessors, six orders of magnitude) and **throughput `∝ N`** (measured 1.11, CI
  1.07–1.15, 100 Intel chips). The network, not the transistor, is the bottleneck:
  performance grew only linearly with N although transistors got much faster.
- **Transitions.** Shrinking-node scaling is like unicellular protists (linear
  performance in size); multi-core is the transition to multicellularity: once nodes stop
  shrinking, added transistors need added area, the network spans longer distances, and an
  increasing fraction of power goes to the network-on-chip. Communication locality
  (`D_w`, Rent's `p`) is the one lever computers have that organisms do not.

## The data-center regime (our extension)

Data centers are the multicellular case: nodes (GPUs, servers) do not shrink, `N` grows by
adding floor area or rack volume, so `l_0` and `r_0` are constants. Repeating the paper's
sums with fixed `l_0` gives (`rentscale.energytime.datacenter_exponents`):

| term | chip regime (nodes shrink), `D_l = 2` | data-center regime (nodes fixed), layout dimension `D_l` |
|---|---|---|
| `E_net` (cable-metres × energy/bit) | `N^{1/2}` | `N` if `p < 1 − 1/D_l`; `N log N` at equality; `N^{p + 1/D_l}` above |
| links / ports / transceivers | — | `N` if `p < 1`; `N log N` at `p = 1` (full-bisection fat-tree) |
| `E_node` | `N^{1/2}` | `N` |
| `T_net` | `N^0` | `N^0` non-blocking; `N^{ln r / ln λ} = N^{1 − p_hw}` for top-level traffic when oversubscribed `r:1` |
| `T_node` | `N^{−1/2}` | `N^0` |
| `E_sys × T_sys` per node | `N^{−1/2}` — improving (increasing returns) | `N^0` at best — constant returns; worse above the locality bound or with oversubscription |
| power `P` | `N^{1/2}` | `N` at best |

So the paper's own machinery says: the increasing returns of the chip era came from
`l_0 ∝ N^{−1/2}`; without it, **linear returns are the ceiling, and only locality
(`p ≤ 1 − 1/D_l`) keeps the network term from pushing returns below linear**. That is the
formal content of Melanie's sentence in the origin email about Rent's rule providing a path
to linear returns to scale. On a single-storey hall (`D_l = 2`) the bound is `p ≤ 1/2`;
inside a rack or a 3-D package (`D_l = 3`) it is `p ≤ 2/3`; a full-bisection fat-tree
(`p = 1`) violates it in any finite dimension and pays `N log N` in switches and
`N^{p + 1/D_l}` in cable.

## Dictionary: model variables → what we measure

| model | our measurable | where |
|---|---|---|
| `N` | transistors (`G`) or GPUs/nodes inside a module | census (`hardware/`) |
| `w_i`, `p = 1/D_w` | external lanes/ports/Gb/s per module; `p_hw` from the census, `p_w` from bytes per token; locality steps `λ_ℓ = k^{p−1}` (`rent.locality_step_from_p`) | census, Topic 02 |
| `l_i`, `D_l` | cable lengths per level (floor plan, tray runs) | Phase 5 design documents |
| `r_i`, `D_r` | bandwidth growth per level: full bisection = area preserving; oversubscription `r` ≙ `D_r > 2` | `fabric.leaf_modules` (down/up Gb/s) |
| `E_net` | NIC + switch + optics power (+ the cooling they need) per bit moved | `power_sampler.py`, PDU metering (Topic 04) |
| `E_node` | GPU/CPU power per unit of work | `power_sampler.py`, DCGM |
| `T_net` vs `T_node` | bytes per token ÷ link bandwidth vs compute time per token — the roofline balance; steady state ≙ ridge point | Topic 02 inference sweeps |
| steady state / pipelining | continuous batching keeps the network full; bursty arrivals violate it — measured by `H` | Topic 03 |

## Testable hypotheses this adds

- **H-ET1 (regime).** Facility power vs installed transistors across CARC generations
  (Wheeler → Easley, `data/reference/carc_generations.csv`) has exponent ≈ 1 (data-center
  regime), not 0.5 (chip regime); per-node energy–time product is flat or rising.
- **H-ET2 (network share).** The fraction of power in the network (switches, NICs, optics)
  rises with `N` at levels where `p_hw > 1 − 1/D_l` (non-blocking fabrics on a 2-D floor)
  and is flat where `p_hw` is below the bound.
- **H-ET3 (balance).** For inference at steady state, `T_net ≈ T_node` at the boundary that
  binds (NVLink for TP, InfiniBand for PP); the ratio measured from bytes/token and
  tokens/s identifies which level is the bottleneck, as the paper found the wire, not the
  transistor, to be the bottleneck on chips.
- **H-ET4 (slowing is optimal).** As mammals are predicted to slow blood toward the
  capillaries (`D_r = 24/11 > 2`), an energy–time-optimal fabric should be mildly
  oversubscribed toward the leaves rather than non-blocking; Jetstream2's inferred 4.3:1
  and CARC's leaf oversubscription (`TODO(carc)`) are the data points.

## Related work by the same group

- Moses, Forrest, Davis, Lodder & Brown (2008), *Scaling theory for information networks*,
  J. R. Soc. Interface 5:1469 — the chip power data (523 processors) used above.
- Bezerra, Forrest, Forrest, Davis & Zarkesh-Ha (2010), *Modeling NoC traffic locality and
  energy consumption with Rent's communication probability distribution*, SLIP — the
  workload-side distribution Topic 02 fits to data-center traffic.
- Zarkesh-Ha, Bezerra, Forrest & Moses (2010), *Hybrid network on chip (HNOC)*, SLIP.
- DeLong, Okie, Moses, Sibly & Brown (2010), *Shifts in metabolic scaling across major
  evolutionary transitions*, PNAS — the superlinear → linear → sublinear sequence.
- Ozaktas (2004), *Information flow and interconnections in computing: extensions and
  applications of Rent's rule*, J. Parallel Distrib. Comput. — Rent's rule beyond the chip.
