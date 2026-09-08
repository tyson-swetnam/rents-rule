# data/

- `reference/` — curated public tables (checked into git). Every row has a `confidence`
  column: `verify` = entered from memory, check against the cited source before use;
  `measured` = produced by this project's scripts; `unknown` = value not available.
  - `pue_by_facility.csv` — PUE vs facility size/vintage seeds for Topic 04.
  - (hardware tables live in `hardware/reference/`.)
- `raw/` — untouched collector and benchmark output copied from `runs/` (gitignored).
- `processed/` — tidy CSV/Parquet produced by `rentscale` (gitignored). Regenerate from raw.

Keep provenance: every processed file should be traceable to a `runs/<id>/meta.json`.
