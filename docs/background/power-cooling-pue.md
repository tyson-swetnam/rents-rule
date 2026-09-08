# Power, cooling, and PUE — primer

## PUE

`PUE = E_facility / E_IT` over a period (ISO/IEC 30134-2; The Green Grid). `E_IT` is
what servers, storage, and network draw; the rest is cooling, power conversion and
distribution losses, lighting. Typical values (`data/reference/pue_by_facility.csv`,
all `verify`): hyperscale fleets ≈ 1.08–1.2; industry survey averages ≈ 1.55–1.6 (Uptime
Institute, 2018–2024), down from ≈ 2.5 in 2007; enterprise rooms and closets ≈ 1.8–2.5;
liquid-cooled HPC halls with heat reuse ≈ 1.03–1.06 (NREL ESIF).

A minimal model separates fixed and proportional overhead:

```
PUE(L) = 1 + (P_fixed + c·L) / L = 1 + c + P_fixed / L
```

PUE falls with IT load `L` (utilization and size) and asymptotes to `1 + c`; technology
(free cooling, liquid cooling, higher voltages) lowers `c`. Tyson's observation — new
large centers ≈ 1.1–1.2, older ≈ 1.5–1.6 — is a statement about both `c` and `P_fixed/L`.
`rentscale.scaling.fit_pue_model` fits `(P_fixed, c)` to `(L, PUE)` data.

PUE is a ratio and hides absolute efficiency: a hall full of idle servers can have an
excellent PUE. Pair it with useful work per joule (Topic 04, H4.4).

## Power delivery as a network

utility (MV) → transformer → switchgear → UPS → PDU → busway → rack PDU → PSU (AC→DC 12/48 V)
→ VRM (→ ~1 V) → die. Each stage converts or distributes; losses are `I²R` in conductors
and a few percent per conversion. Keeping losses a fixed fraction while rack power climbs
requires higher distribution voltage (48 V rack buses; ±400 V / 800 V DC proposals for
multi-hundred-kW racks). Number of stages grows roughly logarithmically with size; the
tree is an area-preserving-branching network in the MST sense when current density is held
constant.

## Cooling as a network

Air: CRAH/CRAC → raised floor or ducts → cold aisle → server fans → hot aisle → return.
Liquid: chiller or dry cooler → CDU → manifolds → rack → cold plates (or immersion).
Heat removal rate `Q = ṁ c_p ΔT`; capacity is linear in flow, but pumping power grows
faster than flow (`∝ ṁ³` in pipes at fixed geometry), and pipe network length scales with
floor geometry. Rack heat flux: ~5–10 kW (2010s) → 30–40 kW (2023 GPU racks) → ~120 kW
(2025 NVL72-class) with roadmaps beyond 500 kW; air cooling saturates near 20–30 kW/rack.

## What to collect at CARC

- Node: `nvidia-smi --query-gpu=power.draw`, RAPL (`/sys/class/powercap/intel-rapl*/energy_uj`),
  `ipmitool dcmi power reading` (chassis; BMC access) — `telemetry/collectors/power_sampler.py`.
- Facility (from the building management system): PDU branch circuits, UPS in/out,
  chiller/pump/fan power, chilled-water supply/return temperature and flow.
- Design documents: one-line electrical diagram, mechanical schematic, floor plan — the
  network levels, lengths, and capacities for the scaling question.

## Metrics operators use (for comparability)

PUE, partial PUE (pPUE) per subsystem, WUE (L/kWh), CUE (kg CO₂/kWh), ERE (energy reuse
effectiveness), rack density (kW/rack), inlet temperature class (ASHRAE A1–A4).
