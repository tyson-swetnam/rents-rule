# Rent's rule — primer

## Statement

For a block of logic with `G` gates and `T` external terminals (pins),

```
T = t · G^p,      0 ≤ p ≤ 1
```

E. F. Rent observed it in IBM mainframe partitioning data in 1960; Landman & Russo (1971)
published it, named it, and identified three regions:

- **Region I** — the power law holds over several decades of `G` (typical `p ≈ 0.5–0.8`).
- **Region II** — for the largest blocks (a whole chip, a board) `T` falls below the law:
  the package is pin-limited. This is *not* a failure of locality but a design constraint.
- **Region III** — very small blocks deviate upward (a gate has a fixed few pins).

## Interpretations of `p`

- `p = 1`: terminals proportional to gates; no locality (a random graph, or a system
  wired for full bisection bandwidth).
- `p = 0`: fixed I/O regardless of size (a self-contained module).
- `p = 1 − 1/d`: the maximum exponent a system can have and still be laid out in `d`
  dimensions with bounded wire density (Ozaktas 1992; Christie & Stroobandt 2000).
  Equivalently the **effective dimension** of a system with exponent `p` is `d_eff = 1/(1−p)`.
  A `d`-dimensional mesh has `p = 1 − 1/d` exactly (a cube of side `s` has `s^d` nodes and
  `2d·s^{d−1}` boundary links).
- Brains: Bassett et al. (2010) measured `p ≈ 0.75–0.8` in C. elegans and human cortex,
  similar to VLSI, interpreted as near-optimal use of 3D wiring.

## Measuring `p`: recursive bisection

Landman & Russo's method for a netlist: recursively bisect the graph (min-cut), record
`(G, T)` for every sub-block, fit the log-log slope. `rentscale.topology.recursive_bisection_points`
does this with Kernighan–Lin bisection on any graph — including a *weighted traffic graph*
(edge weight = bytes exchanged), which yields a **workload** Rent exponent. Heirman et al.
(2008) applied this to parallel programs.

For a physical hierarchy (die, node, rack, …) we do not need bisection: the modules are
given, and `(G, T)` per module is a census. `rentscale.inventory.census` resolves a YAML
hierarchy against the reference tables.

## Cost scaling implied by `p`

Hierarchical system, radix `k`, `N = k^L` units, `t·G^p` links per module of `G` units.

**Installed links** (ports, transceivers, switch ports):

```
links(N) = Σ_{ℓ=0}^{L} (N/k^ℓ) · t k^{ℓp} = tN Σ_ℓ k^{ℓ(p−1)}
```

- `p < 1` → geometric sum converges → **linear in N**.
- `p = 1` → every level costs `tN` → **N log N** (the fat-tree's well-known switch cost).

**Wire length** in `d` dimensions (module of `G` units spans `G^{1/d}`):

```
wire(N) = tN Σ_ℓ k^{ℓ(p − 1 + 1/d)}
```

- linear iff `p < 1 − 1/d`; `N log N` at equality; `N^{p+1/d}` above (Donath 1979).

This is the precise version of "communication locality gives linear communication cost as
long as the fraction of distant communication is a fixed inverse of distance": the
fraction of traffic escaping a module of linear size `D` must fall at least as `1/D`.

## Terminals for data centers: lanes, ports, or bandwidth?

Historically `T` counted pins. At data center scale three definitions are defensible and
give different exponents, because lane speed has grown ~10× per decade while pin counts
grew slowly:

| `T` | what it counts | where it breaks |
|---|---|---|
| lanes | differential pairs per direction | ignores per-lane rate (PCIe 3 vs 5, EDR vs NDR) |
| ports | cables | a QSFP-DD 400G port and a 10G SFP+ count the same |
| Gb/s | line rate | what operators actually provision and measure |

We report all three; Topic 01 asks which one is stable.

## Hardware vs workload

`p_hw` from installed capacity says how much locality the *designers* assumed;
`p_w` from bytes actually moved per unit work says how much the *workload* has. The
ratio of the two locality steps, level by level, is the slack or the bottleneck.
