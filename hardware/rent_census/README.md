# rent_census/

`rent_census.py` turns `hardware/reference/hierarchy_template.yaml` into the census table
and the fits. Try it on the illustrative group first:

```bash
python hardware/rent_census/rent_census.py hardware/reference/hierarchy_template.yaml --group example
```

Expected shape of the result: a large negative local exponent at the die → node boundary
(the node is pin-limited relative to its GPUs), `p = 1` across a full-bisection fabric,
and a steep drop at the facility → WAN boundary. Then fill the `carc` group from the
inventory outputs and rerun with `--group carc --fabric runs/census/fabric/ibnetdiscover.txt`.
