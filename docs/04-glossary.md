# Glossary

- **Rent's rule** — empirical power law `T = t·G^p` between the number of external
  connections (terminals) of a logic block and the number of gates inside it. Named for
  E. F. Rent (IBM, 1960 memos); published by Landman & Russo (1971).
- **Rent exponent `p`** — slope of `log T` vs `log G`; `0 ≤ p ≤ 1`. `p = 1`: no locality
  (terminals proportional to gates); small `p`: strong locality.
- **Rent coefficient `t`** — terminals per gate at `G = 1`.
- **Region I / II / III** — Landman & Russo's regimes: the power law (I); the pin-limited
  regime for large blocks where `T` grows slower than the law (II); and the small-block
  deviation (III).
- **Terminal / gate** — in this project generalized to *external lanes, ports, or Gb/s* and
  *transistors* of a module at any level of the data center hierarchy.
- **Locality step `λ`** — fraction of children's external capacity (or traffic) that leaves
  the parent module.
- **Hardware vs workload exponent** — from installed capacity vs from bytes actually moved
  per unit work.
- **Fat-tree** — a tree network whose link capacity grows toward the root (Leiserson
  1985); the commodity version (Al-Fares et al. 2008) uses `k`-port switches in three
  tiers with `k³/4` hosts and full bisection bandwidth.
- **Bisection bandwidth** — minimum bandwidth across any cut splitting the system in
  halves. "Full bisection" = every host can talk at line rate to any other simultaneously.
- **Oversubscription `r`** — ratio of downlink to uplink capacity at a switch level;
  `r = 1` non-blocking. For a uniform tree, `p = 1 − ln r / ln k`.
- **Bus bandwidth (NCCL)** — per-rank bandwidth normalized so different collectives are
  comparable with the hardware link rate.
- **Self-similar traffic / long-range dependence (LRD)** — statistical scaling of a time
  series under aggregation; autocorrelations decay as a power law.
- **Hurst exponent `H`** — `0.5 < H < 1` for LRD; from R/S, aggregated variance, DFA,
  periodogram, or wavelet estimators.
- **fBm / fGn** — fractional Brownian motion and its increments, fractional Gaussian noise;
  the canonical self-similar Gaussian model with parameter `H`.
- **1/f noise** — `S(f) ∝ f^{−β}`; for fGn `β = 2H − 1`.
- **Metabolic scaling theory (MST)** — Kleiber's law `B ∝ M^{3/4}` and its network
  explanation (West, Brown & Enquist 1997): space-filling hierarchical branching with
  invariant terminal units yields quarter-power exponents.
- **Returns to scale** — cost `C ∝ N^γ`: `γ < 1` increasing returns (economies of scale),
  `γ = 1` linear, `γ > 1` diminishing.
- **PUE** — power usage effectiveness, facility energy / IT energy; 1.0 is ideal.
- **WUE** — water usage effectiveness, litres per kWh of IT energy.
- **Dennard scaling** — the 1974 observation that shrinking transistors kept power density
  constant; it ended around 2005.
- **TP / PP / DP** — tensor, pipeline, and data parallelism; they move very different
  volumes across GPU and node boundaries.
- **DCGM** — NVIDIA Data Center GPU Manager; `dcgmi dmon` exposes NVLink/PCIe byte counters.
- **umad** — user-space InfiniBand management datagram device, needed by `ibnetdiscover` and `perfquery`.
- **PUE floor** — `1 + c`, the asymptote of `PUE(L) = 1 + (P_fixed + cL)/L`.
- **`d_eff`** — `1/(1 − p)`, the dimension in which a system with Rent exponent `p` could be
  wired with bounded density.
- **Energy–time product** — `E_sys × T_sys`, the quantity Moses et al. (2016) minimize; the
  computer architect's energy–delay product. Its per-node exponent tells the returns regime.
- **`D_l`, `D_r`, `D_w`** — the three scaling dimensions of that model: layout (lengths),
  thickness/bandwidth (`2` = area preserving), and communication (`p = 1/D_w`).
- **Area-preserving branching** — total cross-section (flow capacity) conserved across a
  branching; `D_r = 2`; the fabric analogue is full bisection bandwidth.
- **Steady state / pipelining** — supply equals demand and the network is always full; the
  model's time assumption; the roofline ridge point in our measurements.
- **Service volume / isochronic region** — the tissue served by one capillary; the chip area
  reachable within one clock; the model's "node".
