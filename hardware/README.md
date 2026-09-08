# hardware/ — the static Rent census

Answers Topic 01: for every module (die → node → rack → leaf group → pod → facility), how
many transistors are inside and how many lanes / ports / Gb/s leave.

```
inventory/
  inventory_node.sh     run on ONE node of each type (srun -N1): CPUs, GPUs, NVLink topology,
                        PCIe, HCAs, NICs — text/CSV/JSON outputs under runs/census/<host>/
  slurm_inventory.sh    run on a login node: sinfo/scontrol, partitions, node features, and
                        `scontrol show topology` if the topology plugin is configured
  fabric_discover.sh    ibnetdiscover / ibswitches / iblinkinfo (needs umad access), lldpctl
  parse_inventory.py    turns the above into per-node G and T (uses rentscale.inventory)
reference/
  transistor_counts.csv published transistor counts (with `confidence` and `aliases` for matching)
  link_bandwidths.csv   lanes and Gb/s per link type
  hierarchy_template.yaml  the module tree: an illustrative `example` group + `carc` TODOs
rent_census/
  rent_census.py        resolve the YAML (+ optional fabric graph) → census.csv, fits, λ profile
```

## Workflow

```bash
bash hardware/inventory/slurm_inventory.sh runs/census
python hardware/inventory/parse_inventory.py --slurm runs/census        # node types → which nodes to srun
srun -p <partition> -N1 -c1 -t 10 bash hardware/inventory/inventory_node.sh runs/census
bash hardware/inventory/fabric_discover.sh runs/census                  # on a node with /dev/infiniband/umad access
python hardware/inventory/parse_inventory.py runs/census                # per-node G, T
python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml --group example
python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml --group carc \
       --fabric runs/census/fabric/ibnetdiscover.txt
```

## Conventions

- Gates = transistors. Unknown parts (most NICs, Intel Xeons, most switch ASICs) are
  listed in an `unknown_parts` column, never guessed. Report cores / FLOP/s / watts as
  secondary size measures where transistor counts are missing.
- Terminals are reported three ways (`lanes`, `ports`, `gbps`); see
  `docs/background/rents-rule.md`.
- Nothing here needs root. `ibnetdiscover` needs umad access; ask CARC ops to run
  `fabric_discover.sh` on the subnet-manager host if you lack it.
