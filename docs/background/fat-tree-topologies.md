# Fat-trees, oversubscription, and the Rent exponent of a fabric

## Fat-trees

Leiserson (1985): a tree whose links get "fatter" toward the root so that bandwidth does
not collapse at the top; a fat-tree of a given volume can simulate any other network of
that volume with only polylogarithmic slowdown. Al-Fares, Loukissas & Vahdat (2008): the
commodity version with identical `k`-port switches — `k` pods, each with `k/2` edge and
`k/2` aggregation switches, `(k/2)²` core switches, `k³/4` hosts, full bisection bandwidth.
HPC fabrics (InfiniBand, Slingshot) are usually 2- or 3-level fat-trees, often *tapered*
(oversubscribed) at the leaf.

## Rent exponent of a tree fabric

Take a uniform tree with radix `k` (children per switch) and oversubscription `r` at each
level (downlink capacity / uplink capacity). A level-ℓ module contains `G = k^ℓ` hosts
and has `T = k^ℓ / r^ℓ` uplinks, so

```
T = G^{1 − ln r / ln k}      ⇒      p = 1 − ln r / ln k
```

- `r = 1` (non-blocking): `p = 1`. The fabric assumes no locality; cost `N log N`.
- `r = 2, k = 32`: `p = 0.8`. `r = 4, k = 32`: `p = 0.6`.
- `r = k` (a plain tree with one uplink per switch): `p = 0`.

`rentscale.topology.hierarchical_tree(fanouts, oversubscription)` builds such trees with
per-level `k` and `r`; `tapered_exponent(k, r)` is the closed form; `fat_tree(k)` builds
the Al-Fares topology (`p = 1` exactly, test-covered).

## Other topologies

| topology | Rent exponent (links vs nodes) | note |
|---|---|---|
| `d`-dimensional mesh / torus | `1 − 1/d` | 2D: 0.5; 3D: 0.667; 6D torus (K computer): 0.833 |
| hypercube | → 1 (`T = G log₂(N/G)`-ish) | not a pure power law |
| dragonfly | ≈ 1 within a group, then a step | group = locality unit |
| NVLink all-to-all in a node (NVSwitch) | 1 within the node | followed by the node-boundary step |

## Reading a real fabric

`ibnetdiscover` lists every switch and HCA with each link's remote end and rate
(`4xHDR`). `rentscale.fabric.parse_ibnetdiscover` turns it into a graph;
`leaf_modules` gives, per leaf switch, hosts, downlinks, uplinks, lanes, Gb/s, and the
oversubscription — the first Rent points above the node without any assumptions.
`scontrol show topology` (if the Slurm topology plugin is configured) gives the same
grouping without link rates.

## The hardware / workload distinction

A full-bisection fat-tree has `p_hw = 1`; it can *serve* any workload exponent
`p_w ≤ 1`. The question "how far down can a workload be pushed" is whether `p_w` (and the
locality steps `λ_w`) stay below the installed profile at every level — Topic 02.
