# Self-similar traffic and Hurst exponents — primer

## Definitions

A stationary series `X(t)` (bytes per 100 ms, say) is **exactly second-order self-similar**
with parameter `H` if the block-mean series `X^{(m)}` (averages over `m` consecutive
samples) satisfies `Var(X^{(m)}) = m^{2H−2} Var(X)` and has the same autocorrelation for
every `m`. Consequences for `0.5 < H < 1`:

- autocorrelation `ρ(k) ∝ k^{2H−2}` — **long-range dependence** (non-summable);
- spectrum `S(f) ∝ f^{−β}` at low `f` with `β = 2H − 1` — **1/f-type noise**;
- aggregation does not smooth: bursts exist at every time scale.

Fractional Gaussian noise (fGn), the increments of fractional Brownian motion
(Mandelbrot & Van Ness 1968), is the canonical model; `rentscale.hurst.fgn` synthesizes it
exactly (Davies–Harte circulant embedding) for calibrating estimators.

## Why traffic is self-similar (Willinger et al. 1997)

Superpose many ON/OFF sources whose ON (or OFF) durations are heavy-tailed with tail index
`1 < α < 2`. The aggregate converges to fGn with `H = (3 − α)/2`. Heavy-tailed file sizes,
session lengths — and, for inference, prompt and output lengths — are the mechanism. This
gives a **controlled experiment**: inject Pareto(α) output lengths and predict `H`.

## Estimators (all in `rentscale.hurst`)

| estimator | statistic vs scale | slope → H | notes |
|---|---|---|---|
| R/S (Hurst 1951; Mandelbrot–Wallis) | rescaled range `R/S(n)` | `H` | biased toward 0.5–0.6 for short windows |
| aggregated variance | `Var(X^{(m)})` | `2H − 2` | simple, sensitive to non-stationarity |
| DFA-1 (Peng 1994) | fluctuation `F(n)` of detrended profile | `α = H` for fGn | robust to linear trends |
| periodogram (Welch, log-binned) | `S(f)` | `1 − 2H` | needs long segments for low `f`; check `β = 2H − 1` |
| wavelet (Abry–Veitch 1998) | scalogram | `2H − 1` | not implemented yet |

Use at least three; agreement within ±0.05 is the sanity check. Disagreement usually
means periodic components (scheduler cycles, checkpoints), level shifts (job starts), or
too-short records. Taqqu, Teverovsky & Willinger (1995) compare the estimators.

## Practicalities for counter data

- Sample cumulative byte counters at 100 ms; convert to rates with
  `rentscale.counters.rates_from_cumulative` (handles wrap; IB `port_xmit_data` is in
  4-byte units).
- Detrend by subtracting a slow moving average if the load ramps; analyze windows of
  stationarity (≥ 2¹⁴ samples ≈ 27 min at 100 ms; days for `H` at hour scales).
- Report `H` with the scale range used (e.g., 0.1 s – 100 s) — self-similarity in real
  systems holds over a finite range.

## Space and time together

Rent's rule is the spatial scaling law (module size); self-similarity the temporal one
(bin size). Both are power laws under aggregation and both are measured from the same
counters. Whether the two exponents are related in data centers (as suggested for
networks-on-chip by Soteriou, Wang & Peh 2006) is an open question this project can test.
