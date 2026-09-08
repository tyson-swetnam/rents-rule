# CLAUDE.md

Guidance for AI coding/analysis agents working in this repository (Claude Code, Claude
Science, or any agent honoring the `CLAUDE.md` / `AGENTS.md` convention; `AGENTS.md` is a
symlink to this file).

## What this project is

A measurement and theory project on the **scaling of modern computing** — Rent's rule
(wires vs. transistors), communication locality under load, self-similar (Hurst / 1/f)
traffic, and power/cooling networks — across the data center hierarchy
die → package → node → rack → pod → facility → WAN, framed by metabolic scaling theory.
The measurements target the clusters operated by UNM CARC. See `README.md`,
`docs/01-research-questions.md`, and `docs/02-measurement-plan.md`.

## Layout

- `topics/` — one dossier per research question (the "what"). Edit these when the
  science changes.
- `docs/` — origin email, plan, background primers, references, glossary.
- `hardware/` — static census scripts + reference tables + hierarchy YAML + census tool.
- `benchmarks/` — active experiments and Slurm templates.
- `telemetry/` — passive counter collectors (stdlib-only Python so they run on any node).
- `src/rentscale/` — the analysis package (incl. `energytime.py`, the Moses et al. 2016 model and its
  data-center regime — keep its exponents consistent with the paper's Table 1); `tests/` — pytest on synthetic data.
- `data/reference/` — curated public tables; `data/raw|processed/` — gitignored outputs.

## Rules that matter here

1. **Do not invent hardware facts.** Anything about CARC's clusters (node types, GPU
   models, fabric topology, switch models, uplinks) must come from the inventory scripts
   or from Tyson. Placeholders are `TODO(carc)` in YAML/Markdown. Reference tables
   (`hardware/reference/*.csv`, `data/reference/*.csv`) carry a `confidence` column;
   anything entered from memory is `verify` until checked against a primary source.
2. **Counters, never payloads.** Telemetry reads byte/packet counters from sysfs,
   `nvidia-smi`, `dcgmi`, `perfquery`, SNMP. No packet capture, no flow logs with
   addresses, nothing that identifies other users' jobs.
3. **Scripts degrade gracefully.** Every collector/inventory script must run on a node
   without GPUs, without InfiniBand, or without root, and record what it skipped.
4. **Analysis code is tested on synthetic data with known answers** before it touches
   real measurements (fat-tree ⇒ p = 1, d-mesh ⇒ p = 1 − 1/d, fGn ⇒ known H). Keep
   `make test` green.
5. **Units.** Bytes (not bits) in code and CSV columns unless the column name says
   `gbps`. Transistors in billions in the reference table (`transistors_billion`).
   Timestamps are UTC ISO-8601 or `time.monotonic()`-based seconds, named accordingly.
6. **Run provenance.** Benchmark and telemetry runs write into `runs/<date>-<label>/`
   with `meta.json` (git SHA, Slurm job id, node list, command line).

## Commands

```bash
make venv && make test          # local dev
rentscale demo                  # synthetic end-to-end
rentscale fit-rent table.csv --g-col transistors --t-col lanes
rentscale hurst series.csv --column tx_bytes_per_s
rentscale census hardware/reference/hierarchy_template.yaml
```

## Change & commit policy

- **Claude Code:** after a prompt that modifies files, commit immediately with a message
  starting with a verb (Add/Update/Fix/Remove/Refactor), first line < 72 chars.
- **Claude Science:** do not auto-commit; produce artifacts and a diff, commit only on
  explicit instruction.
- Never commit anything under `data/raw/`, `data/processed/`, or `runs/`.
