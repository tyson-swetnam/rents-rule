# Topic 04 — Power and cooling networks

## The question as asked

> I'm also interested in looking at scaling relationships with other networks that serve
> data centers, esp power and cooling, and how they change with scale. — Melanie

> I expect that data center power use efficiency (PUE) goes up with size (and newer tech)
> — the newest data centers are saying they have PUE of ~1.1–1.2; older data centers are
> ~1.5–1.6. — Tyson

## Sharpened statement

Power delivery and heat removal are branching distribution networks, exactly the objects
metabolic scaling theory (West, Brown & Enquist 1997; Banavar, Maritan & Rinaldo 1999)
was built for:

| Biology | Data center power | Data center cooling |
|---|---|---|
| heart → aorta → arteries → capillaries | utility → substation → switchgear/UPS → PDU → busway → rack PDU → PSU → VRM → die | chiller / tower → CDU → manifold → cold plate; or CRAH → plenum → rack → heat sink |
| pressure, flow, conductance | voltage, current, conductance (`I²R` losses) | ΔT, mass flow, thermal conductance |
| terminal units invariant (capillaries) | VRM/die power ≈ fixed per chip generation | cold plate / heat sink per chip |
| space-filling in 3D ⇒ `B ∝ M^{3/4}` | single-storey halls are ~2D ⇒ expect `2/3`-like exponents? | same |

Quantities:

- **PUE** = total facility energy / IT energy. A minimal model is
  `PUE(L) = 1 + (P_fixed + c·L)/L` for IT load `L`: it falls with load and size and
  asymptotes to `1 + c`. Economies of scale come from `P_fixed` amortization, larger
  and more efficient chillers, free cooling, and higher utilization.
- **Heat flux per rack**: ~5–10 kW (2010s air-cooled) → 30–40 kW (2023 GPU racks) →
  ~120 kW (2025 NVL72-class) with roadmaps to hundreds of kW. Air cooling saturates around
  20–30 kW/rack; above that the network must carry liquid.
- **Distribution losses** scale like `I²R`; keeping them a fixed fraction of load as size
  grows requires higher distribution voltage (48 V racks, ±400/800 V DC proposals) — the
  electrical analogue of "area-preserving branching".

## Hypotheses

- **H4.1** PUE vs facility IT capacity across public data is a decreasing power law with a
  small exponent and a floor near 1.05–1.1; newer facilities sit on a lower curve
  (technology shifts the curve, size moves along it). Seed data: `data/reference/pue_by_facility.csv`.
- **H4.2** Cooling capacity is linear in IT load (energy conservation) but the *network*
  serving it (pipe length, pump/fan power, number of hierarchy levels) scales sublinearly,
  with an exponent set by the floor geometry (2D ⇒ closer to 2/3 than 3/4).
- **H4.3** Per-transistor power ("metabolic rate per cell") falls across chip generations
  but per-*rack* power rises, so the cooling network's terminal unit is no longer invariant —
  a break with the MST assumption that predicts where returns diminish.
- **H4.4** For CARC specifically: node power under Topic 02/05 benchmarks scales with
  delivered work as `P ∝ W^{α}` with `α < 1` at high utilization (fixed idle power), i.e.
  utilization is the dominant efficiency lever for a small center.

## What CARC can measure

- Node power: `telemetry/collectors/power_sampler.py` (GPU via `nvidia-smi`, CPU via
  RAPL `powercap`, chassis via `ipmitool dcmi power reading` where permitted).
- Facility: `TODO(carc)` — what the building management system exposes: PDU/branch-circuit
  metering, UPS input/output, chiller and pump power, chilled-water supply/return
  temperatures and flow. With those, a partial PUE for CARC's hall(s) and its time series.
- Design documents: rack count, PDU tree, pipe and duct runs — enough to count hierarchy
  levels and lengths for the network-scaling question.

## Site specifics (2026-09)

- CARC facility (docs/about/facilities): 1,200 sq ft, **270 kVA UPS**, three Liebert AC units
  ("990 tons" as written — verify, likely 99), multiple 10 Gbps campus links + dedicated
  10 Gbps Science DMZ, 100 Gbps to ESnet and the Western Regional Network. No PUE published.
- Jetstream2's primary cloud sits in Indiana University's data center; no PUE in its docs.
- A rack-density estimate for Easley follows from the node map once per-node power is
  sampled (H4.4): 4 H100 nodes and 9 L40S nodes are the hot rows.

## What must come from elsewhere

- Hyperscaler PUE/WUE disclosures (Google, Meta, Microsoft annual reports), Uptime
  Institute surveys, LBNL United States data center energy reports (Shehabi et al. 2016,
  2024), NREL ESIF (liquid-cooled, PUE ≈ 1.03–1.04), NAIRR partner facilities.
- Chip-level power vs transistor tables across generations (vendor TDPs; in
  `hardware/reference/transistor_counts.csv`).

## Literature

- West, Brown & Enquist 1997; Banavar, Maritan & Rinaldo 1999 (network origin of scaling).
- Moses, Bezerra, Edwards, Brown & Forrest 2016, *Energy and time determine scaling in biological and computer designs*.
- Barroso, Hölzle & Ranganathan 2018, *The Datacenter as a Computer*, 3rd ed. (PUE, power provisioning).
- Masanet, Shehabi, Lei, Smith & Koomey 2020, *Recalibrating global data center energy-use estimates*, Science.
- Shehabi et al. 2016 / 2024, *United States Data Center Energy Usage Report* (LBNL).
- Ruch, Brunschwiler, Escher, Paredes & Michel 2011 (see Topic 06).
