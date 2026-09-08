# Topic 03 — Time-domain scaling: 1/f traffic and Hurst exponents across the hierarchy

## The question as raised

> 1/f spectral frequencies are how ethernet traffic is classically measured (Hurst
> exponents from Mandelbrot) and exhibit strong scaling with known exponents. — Tyson

## Sharpened statement

Rent's rule is a scaling law under *spatial* aggregation (bigger modules); self-similar
traffic is a scaling law under *temporal* aggregation (longer bins). Leland, Taqqu,
Willinger & Wilson (1994) showed Ethernet LAN traffic is statistically self-similar with
Hurst exponent `H ≈ 0.7–0.9`: burstiness does not average out when bins are aggregated,
the autocorrelation decays as a power law, and the spectrum is `S(f) ∝ f^{−β}` with
`β = 2H − 1` for fractional Gaussian noise. Willinger et al. (1997) explained it as the
superposition of ON/OFF sources with heavy-tailed ON/OFF periods (tail index `α` ⇒
`H = (3 − α)/2`, Taqqu's theorem).

Questions for the data center hierarchy:

1. What is `H` for a single GPU node's InfiniBand port under (a) production HPC load,
   (b) a controlled inference load with Poisson arrivals and light-tailed lengths,
   (c) the same with heavy-tailed prompt/output lengths?
2. Is `H` invariant when traffic is aggregated *spatially* (port → leaf switch → spine →
   campus uplink)? Self-similarity predicts invariance under temporal aggregation; spatial
   aggregation of independent heavy-tailed sources also preserves `H`, but correlated
   collective operations (all-reduce barriers) may not.
3. Does `β` from the periodogram agree with `2H − 1` from R/S, DFA, and aggregated-variance
   estimators? Disagreement flags non-stationarity or periodic components (job scheduling,
   checkpoint intervals).

## Hypotheses

- **H3.1** Production HPC fabric traffic at CARC has `H ∈ [0.7, 0.9]` at the port level.
- **H3.2** With Poisson request arrivals and exponential-ish output lengths, inference
  traffic has `H ≈ 0.5` at time scales above the per-request duration; injecting
  Pareto-distributed output lengths with tail index `α ∈ (1, 2)` produces
  `H ≈ (3 − α)/2` — a controlled, falsifiable prediction.
- **H3.3** `H` is preserved from port to leaf-switch aggregate (independent jobs), but
  drops at the spine when traffic is dominated by a few synchronized collectives.
- **H3.4** Spectral slope and time-domain estimators agree within ±0.05 in `H` once
  scheduler-period spikes are removed.

## What CARC can measure

- `telemetry/collectors/ib_counters.py` — samples `/sys/class/infiniband/*/ports/*/counters`
  at 100 ms (bytes and packets, cumulative), stdlib-only; run for hours–days as a
  low-priority job (`benchmarks/slurm/traffic_capture_passive.sbatch`). It reads counters
  only; it never sees payloads or other users' data.
- `telemetry/collectors/nic_counters.py` — same for Ethernet (`/sys/class/net/*/statistics`).
- `telemetry/collectors/switch_counters.sh` — `perfquery -x` on switch ports (IB) or SNMP
  `ifHCInOctets` (Ethernet), for the spatial-aggregation question (needs ops access).
- `benchmarks/inference/load_generator.py --output-len-dist pareto --pareto-alpha 1.5` for
  the controlled heavy-tail experiment.
- Estimators: `rentscale.hurst` (R/S, aggregated variance, DFA, periodogram; `fgn()`
  generator for calibration). `rentscale hurst series.csv --column tx_bytes_per_s`.

## Site specifics (2026-09)

- CARC exposes a perfSONAR measurement point (perfsonar.alliance.unm.edu) on the campus/WAN
  side and publishes XDMoD usage metrics; both are existing time series for the aggregate
  (facility-level) end of the spatial-aggregation question.
- Easley's fabric is NDR InfiniBand; Hopper's is HDR; Jetstream2's is 100 GbE Clos with
  Cumulus switches (SNMP counters exist on the leaves and spines).

## Literature

- Leland, Taqqu, Willinger & Wilson 1994, *On the self-similar nature of Ethernet traffic (extended version)*.
- Mandelbrot & Van Ness 1968, *Fractional Brownian motions, fractional noises and applications*; Hurst 1951.
- Willinger, Taqqu, Sherman & Wilson 1997, *Self-similarity through high-variability: statistical analysis of Ethernet LAN traffic at the source level*.
- Paxson & Floyd 1995, *Wide area traffic: the failure of Poisson modeling*.
- Taqqu, Teverovsky & Willinger 1995, *Estimators for long-range dependence: an empirical study*.
- Peng et al. 1994 (DFA); Abry & Veitch 1998 (wavelet estimator).
- Benson, Akella & Maltz 2010 — ON/OFF behaviour in data center traffic.
- Soteriou, Wang & Peh 2006, *A statistical traffic model for on-chip interconnection networks* (self-similar NoC traffic; `verify`).
