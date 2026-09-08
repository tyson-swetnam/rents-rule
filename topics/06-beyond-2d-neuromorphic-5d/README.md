# Topic 06 — Beyond 2D: dimensionality bounds, brains, and "five-dimensional" scaling

## The question as raised

> I did some googling and found some scaling papers stating that next-gen compute will need
> to be neuromorphic or at least emulate human brains to move fluid, heat, and power "in 5
> dimensions" — but I couldn't get the full pdf. https://ieeexplore.ieee.org/abstract/document/6044603 — Tyson

The IEEE Xplore document 6044603 appears to be Ruch, Brunschwiler, Escher, Paredes &
Michel (IBM Research – Zurich), *Toward five-dimensional scaling: How density improves
efficiency in future computers*, IBM Journal of Research and Development 55(5), 2011
(`verify` — UNM Libraries should have IBM J. R&D access). Its thesis, from the abstract and
the group's related talks: computing efficiency has tracked *packing density*; the brain is
the existence proof (3D, with a single fluid network doing both power delivery and heat
removal); so future computers should scale into the third dimension with interlayer liquid
cooling and, eventually, electrochemical power delivery — "5D" being the three spatial
dimensions plus the fluid networks for power and heat that make 3D density usable.

## Sharpened statement — the Rent lens on dimensionality

Ozaktas (1992) and Christie & Stroobandt (2000): a system with Rent exponent `p` can be
embedded in `d` dimensions with bounded wiring density only if `p ≤ 1 − 1/d`. Inverting,
the **effective dimension implied by a measured exponent** is

```
d_eff = 1 / (1 − p)        (p = 0.5 ⇒ d_eff = 2;  p = 2/3 ⇒ d_eff = 3;  p → 1 ⇒ d_eff → ∞)
```

A full-bisection fat-tree (`p = 1`) is a system that refuses to be embedded in any finite
dimension — its cost is `N log N` in switches and its cables have to grow without bound.
Bassett et al. (2010) found `p ≈ 0.75–0.8` in C. elegans and human cortical networks,
above the 3D bound, and argued brains sit near the edge of what 3D wiring allows. This
topic asks the same of a data center: at which levels is the hierarchy effectively 2D
(floor plans), 3D (racks, 3D-stacked chips), or "infinite-dimensional" (fat-trees), and
what would moving heat and power in 3D buy in communication terms.

## Hypotheses

- **H6.1** `d_eff` from Topic 01 is ≈ 3 inside the node (NVLink meshes, PCIe trees on a 3D
  board stack), → ∞ across the fabric (fat-tree), and ≈ 2 at the facility (single-storey
  halls, cable trays). The profile of `d_eff` is the "shape" of the data center.
- **H6.2** Liquid cooling is the enabler of density and therefore of higher permissible
  `p` in 3D (`2/3` vs `1/2` in 2D): the cooling network's dimension bounds the
  communication network's exponent — Ruch et al.'s claim restated as a Rent inequality.
- **H6.3** Neuromorphic and brain-like systems achieve `p` near the 3D bound with sparse,
  event-driven traffic (`λ_w ≪ 1` at every level); Partzsch & Schüffny (2012) report Rent
  exponents for neural network models and neuromorphic hardware that can be compared
  directly with Topic 01/02 numbers (`verify`).

## What Moses et al. (2016) adds

`D_l` is explicitly the dimension the nodes fill, and the locality bound `p ≤ 1 − 1/D_l`
is stated as the convergence condition of the network-energy sum. A 3-D data center (racks,
stacked packages, liquid cooling that makes volume usable — the "five-dimensional" argument)
raises the bound from 1/2 to 2/3: the amount of communication per transistor that can leave
a module without super-linear wiring grows with the dimension the cooling network can
serve. **H6.4:** liquid-cooled, 3-D-packaged levels of the hierarchy (NVLink domains,
NVL72-class racks) show `p_hw` between 1/2 and 2/3, air-cooled 2-D levels stay at or below 1/2.

## What CARC contributes

Nothing to measure directly beyond Topics 01–04; this is where their results are combined:
`rentscale.scaling.dimension_from_rent(p)` and the level-by-level `d_eff` profile.
The one physical datum worth collecting is the facility floor plan (rack rows, cable
tray and pipe runs) to test the 2D claim at the top level.

## Literature

- Ruch, Brunschwiler, Escher, Paredes & Michel 2011, IBM J. Res. Dev. 55(5) (`verify` DOI / access).
- Ozaktas 1992; Christie & Stroobandt 2000 (dimension bound).
- Bassett et al. 2010 (brains vs VLSI Rent exponents).
- Partzsch & Schüffny 2012, *Analyzing the scaling of connectivity in neuromorphic hardware and in models of neural networks* (`verify`).
- Moses et al. 2016 — the 2D-vs-3D argument for why computers and organisms scale differently.
- Mead 1990, *Neuromorphic electronic systems*; Davies et al. 2018 (Loihi); Furber et al. 2014 (SpiNNaker).
