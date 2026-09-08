# "Five-dimensional scaling" and brain-inspired density

## The paper

IEEE Xplore document 6044603 (linked in the origin email) appears to be:
Ruch, P., Brunschwiler, T., Escher, W., Paredes, S. & Michel, B. (2011). *Toward
five-dimensional scaling: How density improves efficiency in future computers.* IBM J.
Res. Dev. 55(5), 15:1–15:13 — `verify`; obtain via UNM Libraries (IBM J. R&D is on IEEE
Xplore).

Thesis, from the abstract and the IBM Zurich group's related work (Aquasar hot-water
cooling, interlayer-cooled 3D chip stacks, "electronic blood" redox-flow power delivery):

1. Efficiency gains in computing have tracked *packing density*, not just transistor count.
2. Two-dimensional scaling (Moore/Dennard) is ending; the next gains come from the third
   spatial dimension (chip stacking), which is only usable if heat removal and power
   delivery also become volumetric — fluids through the stack.
3. The brain is the existence proof: ~20 W, volumetric, with one fluid network (blood)
   delivering energy and removing heat, and memory co-located with compute.
4. "Five dimensions" = three spatial dimensions plus the two fluid-carried functions (power in,
   heat out) that must scale together with them. (Restate after reading the paper.)

## Restated as a Rent inequality

Ozaktas: a system with Rent exponent `p` needs `d ≥ 1/(1 − p)` dimensions for bounded
wiring density. A 2D system is limited to `p ≤ 1/2`; 3D allows `p ≤ 2/3`. Higher `p`
means more bandwidth per transistor can leave a module without wiring blow-up — but only
if power and heat can also be moved through the volume. So the cooling network's
effective dimension bounds the communication network's exponent:

```
p_comm ≤ 1 − 1/d_cooling
```

which is a testable form of the paper's claim. Data centers today are 2D at the hall
level (air or liquid loops on a floor), 3D inside racks and packages, and use
"infinite-dimensional" fat-trees to escape the bound at the cost of `N log N` switching.

## Brains as the reference point

- Bassett et al. (2010): Rent exponents of C. elegans and human cortical networks
  ≈ 0.75–0.8, near or above the 3D bound, comparable to VLSI.
- Neuromorphic hardware (TrueNorth, Loihi, SpiNNaker) exploits sparse, event-driven
  communication: very small workload locality steps at every level. Partzsch & Schüffny
  (2012) computed Rent exponents for neural network models and neuromorphic systems (`verify`).
- Moses et al. (2016): organisms vs computers differ in dimension and in whether terminal
  units shrink over time.

## What this project can say

From Topics 01–04: the level-by-level profile of `d_eff = 1/(1 − p_hw)`, the workload
profile `p_w`, and the cooling type per level (air vs liquid). Whether liquid cooling
correlates with a higher installed `p` at the node/rack level is the concrete question.
