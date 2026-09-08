# Topic 05 — Returns to scale: the metabolic-scaling synthesis

## The question as asked

> … metabolic scaling theory suggests size tradeoffs for data centers. Thus far we suspect
> both increasing and diminishing returns to scale for different factors. Traditionally,
> compute has increasing returns to scale, although that is less certain with the end of
> Moore's Law and Dennard scaling. Cooling and power may face diminishing returns. Rent's
> Rule is a pattern that provides a path to linear returns to scale — communication
> locality can result in linear communication cost as a system size increases, as long as
> the fractions of distant vs local communication remain fixed inverses of the distances
> communicated. — Melanie

## Sharpened statement

Write each resource cost as a power of system size `N` (transistors, or IT watts):
`C_i(N) ∝ N^{γ_i}`. Then `γ_i < 1` is increasing returns (economies of scale),
`γ_i = 1` linear, `γ_i > 1` diminishing returns. The cost per unit of compute is
`Σ_i a_i N^{γ_i − 1}`, and an optimal size exists whenever at least one term has
`γ < 1` and one has `γ > 1` (`rentscale.scaling.optimal_size`).

### Where Rent's rule gives linear communication cost

Take a hierarchical system with radix `k`, `N = k^L` units, and Rent exponent `p` so a
module of `G` units has `t·G^p` external links. Summing installed links over all levels:

```
links(N) = Σ_{ℓ=0}^{L} (N / k^ℓ) · t · k^{ℓp} = t N Σ_ℓ k^{ℓ(p−1)}
```

- `p < 1`: the geometric sum converges ⇒ **links ∝ N, linear**.
- `p = 1` (full-bisection fat-tree): every level costs `tN` ⇒ **N log N**.

If links must be *embedded* in `d` dimensions (a module of `G` units has linear size
`G^{1/d}`), wire length at level `ℓ` picks up a factor `k^{ℓ/d}`:

```
wire(N) = t N Σ_ℓ k^{ℓ (p − 1 + 1/d)}
```

which is linear iff `p < 1 − 1/d`, `N log N` at `p = 1 − 1/d`, and `N^{p + 1/d}` above
(Donath 1979; Ozaktas 1992). This is the precise form of Melanie's condition: the fraction
of traffic leaving a module of linear size `D` must fall at least as fast as `1/D` — "fixed
inverses of the distances communicated". In 2D the critical exponent is `1/2`; in 3D it is
`2/3`. Compare MST: a 3D space-filling supply network yields `3/4`; a 2D one `2/3`.

### The table to fill in

| Cost term | Quantity vs `N` | Expected `γ` | Source of the number |
|---|---|---|---|
| Compute capability per $ / per W | transistors, FLOPS | historically `< 1` (Moore, Dennard); now → 1 | vendor price/TDP history (Topic 01 table) |
| Communication links (ports) | `N Σ k^{ℓ(p−1)}` | `= 1` if `p_hw < 1`; `N log N` if `p_hw = 1` | Topic 01 census |
| Communication wiring (bit-metres) | `N Σ k^{ℓ(p−1+1/d)}` | `= 1` iff `p ≤ 1 − 1/d` | Topic 01 + floor plan (`d_eff`, Topic 06) |
| Used bandwidth per unit work | `B_ℓ` | `p_w` (Topic 02) | Topic 02 |
| Power delivery losses | `I²R` over stages | `≈ 1` with rising voltage, else `> 1` | Topic 04 |
| Cooling network | pipe/duct/pump | `< 1` for the network, `= 1` for heat | Topic 04 |
| PUE overhead | `(P_fixed + cL)/L` | `< 1` (economies of scale) | `pue_by_facility.csv` |

## Hypotheses

- **H5.1** A data center has an interior optimum size set by the crossing of the
  compute/PUE economies (`γ < 1`) with power-delivery and cooling diseconomies (`γ > 1`);
  hyperscale campuses are collections of near-optimal halls rather than one huge hall.
- **H5.2** GPU clusters push `p_hw` toward 1 above the node (full-bisection fabrics for
  training), so their communication cost is `N log N` — the price of not exploiting
  locality — while inference fleets can run on tapered fabrics (`p_hw < 1`) because
  `p_w ≪ 1` (Topic 02).
- **H5.3** The end of Dennard scaling moved compute from `γ < 1` toward `γ ≈ 1`, making
  the network and cooling terms decisive — which is why the industry is fighting over
  fabrics (NVLink, UALink, Ultra Ethernet) and liquid cooling rather than over transistors.

## What CARC contributes

The one place where every row of the table can be measured on the same hardware: census
(Topic 01), used bandwidth (Topic 02), traffic statistics (Topic 03), node and (partial)
facility power (Topic 04). `rentscale.scaling` fits the exponents and evaluates the
size-tradeoff model.

## Literature

- Kleiber 1932; West, Brown & Enquist 1997; Banavar et al. 1999, 2010.
- Moses et al. 2016 (biological vs computer designs); Bezerra, Forrest, Moses et al. (`verify` follow-ups).
- Donath 1979, *Placement and average interconnection lengths of computer logic*.
- Ozaktas 1992; Christie & Stroobandt 2000.
- Dennard et al. 1974; Esmaeilzadeh et al. 2011, *Dark silicon and the end of multicore scaling*.
- Leiserson 1985 (fat-tree cost); Al-Fares, Loukissas & Vahdat 2008.
