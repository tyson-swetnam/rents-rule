# Topic 01 — Rent's rule in the hardware hierarchy

## The question as asked

> At multiple scales (e.g., GPU or CPU, server, rack, pod, data center), what is the ratio
> of communication 'wires' or interconnect to number of transistors at that level of
> organization? … if a GPU has 1 billion transistors and 1000 wires connecting to other
> GPUs, and a rack has 1 trillion transistors, does it have 1000 times more wires? If it's
> nonlinear, what is the relationship between compute capacity within a module and
> communication capacity outside that module? — Melanie

> Transistors and wires do not scale one-to-one within a server … Transistor to copper or
> optical wire counts do not account for "bandwidth," usually what is measured. — Tyson

## Sharpened statement

For a module `M` at hierarchy level `ℓ ∈ {die, package, node, rack, pod, facility}` define

- `G(M)` — transistors inside `M` (sum over CPUs, GPUs, and, where known, NICs and switch ASICs).
- `T(M)` — external communication capacity of `M`, measured three ways:
  - `T_lanes` — physical high-speed lanes (differential pairs) leaving `M`
    (NVLink lanes, PCIe lanes, 4 lanes per 4x InfiniBand port, 1–8 lanes per Ethernet port);
  - `T_ports` — physical ports/cables leaving `M`;
  - `T_gbps` — aggregate line rate leaving `M`, in Gb/s (unidirectional).

Rent's rule (Landman & Russo 1971) is the power law `T = t · G^p`. The **hardware Rent
exponent** `p_hw` is the slope of `log T` vs `log G` across levels. We expect it to be
piecewise, so we also define the **locality step** at each boundary,

```
λ_ℓ = T(M_ℓ) / Σ_{children c ⊂ M_ℓ} T(c)
```

the fraction of the children's external capacity that survives as external capacity of
the parent. For a full-bisection fat-tree `λ = 1` at every switching level; for a 2:1
oversubscribed level `λ = 0.5`; at a server boundary it can be far smaller (below).

## Why the answer will be piecewise: a worked example with vendor numbers

An 8-GPU A100 node (DGX-A100-class; values from public specifications, see
`hardware/reference/*.csv`):

| Module | `G` (transistors) | `T_lanes` | `T_gbps` | lanes per 10⁹ transistors |
|---|---:|---:|---:|---:|
| one A100 die | 5.42 × 10¹⁰ | 12 NVLink3 links × 4 lanes + 16 PCIe4 lanes = **64** | 12 × 400 + 16 × 16 ≈ **5,056** | 1.18 |
| the node (8 GPUs + 2 CPUs, ignoring NICs' own transistors) | ≈ 5.2 × 10¹¹ | 8 HDR IB ports × 4 lanes = **32** | 8 × 200 = **1,600** | 0.06 |

Going from die to node multiplies `G` by ~10 but *divides* `T` by 2 (lanes) or 3
(bandwidth). The local exponent across that boundary is `p ≈ ln(0.5)/ln(9.6) ≈ −0.3`.
The node boundary is a Region-II "pin-limited" step (Landman & Russo's term): the design
assumes that most GPU traffic stays inside the node. Above the node, a fat-tree fabric
restores `p ≈ 1` (or `1 − ln r / ln k` when tapered, see
[fat-tree-topologies.md](../../docs/background/fat-tree-topologies.md)). At the facility
boundary the WAN uplinks are another step down.

So the interesting result is not one number but the **profile of `p` and `λ` across
levels** — which is exactly the "how much locality is designed in at each scale" question.

## Hypotheses

- **H1.1** Die/package level: pins vs transistors follows the classic microprocessor Rent
  curve with `p ≈ 0.4–0.6` when counting lanes, but the *bandwidth* exponent is higher
  because per-lane rate (SerDes) has grown ~10× per decade while pin counts grew slowly.
  Test with the historical GPU table (K40 → H100 → B200): lanes and Gb/s vs transistors.
- **H1.2** Node boundary: `λ_node` (bandwidth) is in the range 0.03–0.1 for GPU nodes and
  ~1 for CPU-only nodes (a CPU node's PCIe lanes and NIC ports are comparable). Prediction:
  GPU clusters have a *deeper* locality step than CPU clusters.
- **H1.3** Fabric levels: `p_hw = 1 − ln r / ln k` for a tree with radix `k` and
  per-level oversubscription `r`; `p_hw = 1` for full bisection. CARC's fabric: `TODO(carc)`
  extract `k`, `r` per level from `ibnetdiscover` / `scontrol show topology`.
- **H1.4** Facility boundary: WAN uplink capacity vs facility transistors gives the lowest
  `p` of the whole profile; it is set by budget and campus networking, not by locality.
- **H1.5** Across generations at fixed level (e.g., GPU dies 2013–2025), `T_gbps ∝ G^{p_t}`
  with `p_t ≈ 1` (vendors keep NVLink bandwidth per transistor roughly constant), while
  `T_lanes ∝ G^{p_l}` with `p_l ≪ 1`.

## What CARC can measure

| Level | `G` source | `T` source | Script |
|---|---|---|---|
| die / package | `nvidia-smi --query-gpu=name` + `transistor_counts.csv`; `lscpu` model + table | `nvidia-smi topo -m` (NV link counts), `nvidia-smi -q` (PCIe gen/width), `nvidia-smi nvlink -s` | `hardware/inventory/inventory_node.sh` → `rentscale.inventory` |
| node | sum of the above | `ibstat` / `ibv_devinfo` (ports, rate), `ethtool` (NIC speed), `lspci` | same |
| rack / leaf | node inventory × node count per leaf | leaf-switch uplink count and rate from `ibnetdiscover`, `iblinkinfo` | `hardware/inventory/fabric_discover.sh` |
| pod / spine | leaf groups per spine | spine uplinks / core links | same + `scontrol show topology` |
| facility | all clusters | campus and Internet2 circuits (`TODO(carc)` ask UNM IT) | manual → `hierarchy_template.yaml` |

Then `python hardware/rent_census/rent_census.py hierarchy.yaml` fits `p` for each
definition of `T` and prints `λ_ℓ` per boundary.

## What the documentation already tells us (2026-09)

- **CARC Easley**: 65 nodes, 64 cores each; 4 nodes × 2 H100, 9 nodes × 4 L40S (no NVLink on
  L40S), "NDR 800 Gbps" InfiniBand; CPU model and per-HCA rate undocumented.
- **CARC Hopper**: 61 Dell R640/R740 nodes, Xeon Gold 6226R/6242, 37 A100 + V100 condo nodes,
  "HDR 400 Gbps" InfiniBand.
- **Retired CARC generations** (Wheeler QDR 2010 → Gibbs QDR → Xena FDR + K40M → Taos FDR →
  Hopper HDR + A100 → Easley NDR + H100/L40S) form a 15-year series for H1.5:
  `data/reference/carc_generations.csv`.
- **Jetstream2** (primary cloud): 538 Dell nodes on a two-tier Ethernet Clos of 6× SN4600 spines
  and 37× SN2700 leaves, single 100 GbE per CPU host and dual per GPU host, 2× 100 Gbps to the
  data center and 100 Gbps each to Internet2 and ACCESS — an inferred **4.3:1** leaf
  oversubscription (`p ≈ 1 − ln 4.3 / ln 26 ≈ 0.55` if the tree were uniform) against CARC's
  InfiniBand fat-trees. Details: [docs/03](../../docs/03-carc-hardware-inventory.md),
  [docs/05](../../docs/05-jetstream2-inventory.md).

## What Moses et al. (2016) adds

Rent's rule is the third dimension of their network model: `w_i = w_0 λ^{i/D_w}` with
`p = 1/D_w`, next to `D_l` (lengths) and `D_r` (thickness/bandwidth). Their chip optimum is
`D_l = D_r = D_w = 2`, i.e. `p = 1/2` on a 2-D layout; the network-energy sum converges only
if `p ≤ 1 − 1/D_l`. Two consequences for the census:

- **H1.6** For each level, compare `p_hw` with `1 − 1/D_l` of that level's geometry (`1/2` on the
  hall floor, `2/3` inside a rack or package). Levels above the bound (non-blocking fabrics)
  are where cable-metres and network energy grow faster than `N`.
- **H1.7** Full bisection is the fabric analogue of area-preserving branching (`D_r = 2`);
  oversubscription `r` is `D_r > 2`. The model predicts organisms *should* slow flow toward the
  terminals (`D_r = 24/11`); the fabric analogue is a mildly tapered tree. Report each leaf's
  down/up ratio (`fabric.leaf_modules`) as the "blood-slowing" parameter of the fabric.

The locality step and the exponent are linked in closed form for a uniform hierarchy,
`λ_ℓ = k^{p−1}` (`rentscale.rent.locality_step_from_p`), so a measured step converts to a
per-level `p` directly. Primer: [docs/background/energy-time-minimization.md](../../docs/background/energy-time-minimization.md).

## What must come from elsewhere

- Transistor counts for NICs (ConnectX) and most switch ASICs are not published; treat as
  zero with a flag, or bound them (NVIDIA publishes Quantum-2 ≈ 57 B, Spectrum-4 ≈ 100 B,
  NVSwitch-3 ≈ 25 B, BlueField-3 ≈ 22 B — all `verify`).
- Hyperscaler and NAIRR facilities: the same census needs their topology; Melanie's
  contacts. Our census tool accepts any hierarchy YAML.

## Literature (read first)

- Landman & Russo 1971, *On a pin versus block relationship for partitions of logic graphs*.
- Christie & Stroobandt 2000, *The interpretation and application of Rent's rule*.
- Lanzerotti, Fiorenza & Rand 2005, *Microminiature packaging and integrated circuitry: the work of E. F. Rent*.
- Ozaktas 1992, *Paradigms of connectivity for computer circuits and networks* (the `p ≤ 1 − 1/d` bound).
- Bassett et al. 2010, *Efficient physical embedding of topologically complex information processing networks in brains and computer circuits* (Rent exponents in brains ≈ VLSI).
- Greenfield, Banerjee, Lee & Moore 2007, *Implications of Rent's rule for NoC design* (`verify` details).

See [docs/references.md](../../docs/references.md) for full entries.
