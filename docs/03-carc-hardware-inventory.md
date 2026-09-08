# CARC hardware inventory (template — fill from the inventory scripts, not from memory)

Every field marked `TODO(carc)` must come from `hardware/inventory/*.sh` output or from
CARC documentation. Do not guess. When filled, mirror the numbers into
`hardware/reference/hierarchy_template.yaml` so `rentscale census` can use them.

## Clusters

| Cluster | Scheduler / partitions | Node types (count) | Fabric | Storage | Notes |
|---|---|---|---|---|---|
| TODO(carc) | Slurm: TODO(carc) | TODO(carc) | TODO(carc) (HCA, switch model, levels, oversubscription) | TODO(carc) (Lustre/NFS, network) | |
| TODO(carc) | | | | | |

## Node types

One row per distinct (CPU, GPU, HCA/NIC) combination as reported by
`python hardware/inventory/parse_inventory.py --slurm runs/census`.

| Type id | CPU model × sockets | GPU model × count | GPU↔GPU (NVLink links per pair, PCIe gen/width) | HCA (model, ports, rate) | Ethernet (ports, speed) | Count |
|---|---|---|---|---|---|---|
| TODO(carc) | | | | | | |

## Fabric

- Subnet manager host / UFM: `TODO(carc)`
- Switch models and counts per level (leaf / spine / core): `TODO(carc)`
- Downlinks and uplinks per leaf; oversubscription ratio per level: `TODO(carc)`
- `scontrol show topology` configured? `TODO(carc)`
- Rail-optimized (one HCA per rail) or single-rail: `TODO(carc)`

## Facility boundary

- Campus uplinks (count × rate), Internet2 / research network circuits: `TODO(carc)` (UNM IT)
- Storage fabric separate from compute fabric? `TODO(carc)`

## Power and cooling

- IT capacity (kW) and typical load: `TODO(carc)`
- Metering available (PDU branch circuits, UPS in/out, chiller, pumps, chilled-water ΔT/flow): `TODO(carc)`
- Cooling type per row (air / rear-door HX / direct liquid): `TODO(carc)`
- Rack density range (kW/rack): `TODO(carc)`
- PUE if known, and how measured: `TODO(carc)`

## Monitoring already in place

- Prometheus / Grafana / Ganglia / UFM telemetry: `TODO(carc)` — existing time series may
  cover Phase 4 without new collectors.
