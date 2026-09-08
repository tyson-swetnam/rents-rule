# Metabolic scaling theory — what carries over to data centers

## The biological facts

- **Kleiber (1932):** metabolic rate `B ∝ M^{3/4}` across ~20 orders of magnitude of body mass.
  Per-unit-mass metabolic rate falls as `M^{−1/4}`: large organisms are more efficient
  per cell (an economy of scale).
- **Quarter powers** appear throughout: heart rate `∝ M^{−1/4}`, lifespan `∝ M^{1/4}`,
  aorta radius `∝ M^{3/8}`, …
- **Surface-area scaling** would give `2/3` (heat loss through a surface). The observed
  `3/4` needs a different explanation.

## The network explanation (West, Brown & Enquist 1997)

Assume (1) a space-filling hierarchical branching network supplies every cell,
(2) terminal units (capillaries) are size-invariant, (3) the network minimizes transport
energy (area-preserving branching, impedance matching). Then in `d = 3` the exponent is
`d/(d+1) = 3/4`; in 2D it would be `2/3`. Banavar, Maritan & Rinaldo (1999) derived the
same `d/(d+1)` from a more general efficient-transport argument.

## The data center dictionary

| MST ingredient | data center analogue | where it strains |
|---|---|---|
| body mass `M` | transistors / IT watts / floor area | which one is "size"? |
| metabolic rate `B` | facility power (or useful work) | power is provisioned, not scaled |
| supply network | power delivery tree; cooling loop; **and** the communication fabric | three networks, not one |
| invariant terminal unit | a chip's cold plate / VRM; a NIC port | chip TDP is *not* invariant (K40 235 W → H100 700 W) |
| space-filling in 3D | racks fill a hall in ~2D; chips are 3D-stacked; fat-trees are effectively ∞-D | dimension differs per level (Topic 06) |
| minimized transport cost | Rent locality minimizes wire; high-voltage DC minimizes `I²R` | designers, not evolution |

Moses, Bezerra, Edwards, Brown & Forrest (2016) made the first careful version of this
comparison: computers scale differently from organisms partly because chip layouts are 2D
and because the "terminal units" (transistors) shrank over time whereas cells did not.

## Returns to scale as the shared language

In MST, `B ∝ M^{3/4}` is an economy of scale in energy. For data centers we write every
resource as `C_i ∝ N^{γ_i}` and ask, term by term, whether `γ_i` is below, at, or above 1.
The Rent argument (see [rents-rule.md](rents-rule.md)) gives `γ = 1` for communication
links when `p < 1`, and `N log N` when `p = 1`. Topic 05 assembles the table.

## What CARC can add that the literature lacks

All previous "computer allometry" used published specs. CARC can measure, on one system,
installed capacity, delivered capacity, used capacity, and power — the four quantities the
theory relates.
