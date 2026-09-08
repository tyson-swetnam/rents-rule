# Topics — the research questions, one folder each

Each folder is a dossier for one question from the origin email
([docs/00-origin-email-thread.md](../docs/00-origin-email-thread.md)): the question as
asked, a sharpened statement, hypotheses, what CARC can measure, what must come from
elsewhere, the scripts that produce the data, and the literature to read first.

| # | Topic | Raised by | Primary measurable | Instruments |
|---|---|---|---|---|
| [01](01-rents-rule-hardware/) | Rent's rule in the hardware hierarchy — wires (and bandwidth) vs transistors per module | Melanie (hardware question); Tyson (wires ≠ bandwidth) | Hardware Rent exponent `p_hw` per level, and the locality step `λ` at each boundary | `hardware/inventory/*`, `hardware/rent_census/` |
| [02](02-communication-locality-under-load/) | Communication locality under inference load — bytes crossing each boundary per token | Melanie (software question); Tyson (p<1 is how far down a workload can be pushed) | Workload Rent exponent `p_w`, bytes/token per level, variance | `benchmarks/inference/*`, `telemetry/collectors/*` |
| [03](03-traffic-self-similarity/) | Time-domain scaling — 1/f, Hurst exponents across aggregation levels | Tyson | `H` and spectral slope `β` per port and per aggregation level | `telemetry/collectors/ib_counters.py`, `rentscale.hurst` |
| [04](04-power-and-cooling-networks/) | Power and cooling networks — PUE vs size, heat flux, distribution networks | Melanie; Tyson (PUE 1.1–1.2 new vs 1.5–1.6 old) | PUE(size), node power vs work, distribution-network exponents | `telemetry/collectors/power_sampler.py`, `data/reference/pue_by_facility.csv` |
| [05](05-returns-to-scale/) | Returns to scale — the MST synthesis: increasing (compute), linear (communication via Rent), diminishing (power/cooling) | Melanie | Exponent per cost term; size-tradeoff model | `rentscale.scaling` |
| [06](06-beyond-2d-neuromorphic-5d/) | Beyond 2D — dimensionality bounds on Rent exponents, brains, "five-dimensional" scaling | Tyson (IEEE 6044603) | Effective dimension `d_eff = 1/(1−p)` per level | synthesis of 01–04 |

Cross-cutting definitions live in [docs/01-research-questions.md](../docs/01-research-questions.md).
The order of work is in [docs/02-measurement-plan.md](../docs/02-measurement-plan.md).
