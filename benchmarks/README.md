# benchmarks/ — active experiments

| folder | what it measures | tools |
|---|---|---|
| `intra_node/` | delivered GPU↔GPU bandwidth and NCCL collectives for 1, 2, 4, 8 GPUs inside one node (module sizes below the node boundary) | `nvbandwidth` or CUDA samples `p2pBandwidthLatencyTest`; `nccl-tests` |
| `inter_node/` | delivered bandwidth across nodes: raw RDMA, MPI point-to-point and collectives, bisection-like all-to-all for N = 2, 4, 8, 16, … nodes | `perftest` (`ib_write_bw`), OSU micro-benchmarks, `nccl-tests` |
| `inference/` | bytes crossing each boundary per generated token under an LLM serving load, TP inside the node and PP across nodes | vLLM (OpenAI-compatible server) + `load_generator.py` |
| `slurm/` | job templates and the sweep driver; `site.env` holds the CARC-specific settings | Slurm |

All jobs start the passive collectors (`telemetry/collectors/collect_all.sh`) beside the
workload, so every benchmark also yields counter time series, and write
`runs/<timestamp>-<label>-<jobid>/meta.json` for provenance.

## Delivered terminal capacity

For a module of `n` GPUs, NCCL's `busbw` at the largest message size is the per-rank
injection bandwidth the collective actually achieved. Define
`T_del(n) = n × busbw_alltoall(n)` (GB/s) and fit against `G(n) = n × transistors/GPU`.
Compare `p_del` with the installed `p_hw` from the census: where they diverge, the
software stack or the fabric (not the wires) is the limit.

## Setup on CARC

```bash
cp benchmarks/slurm/site.env.example benchmarks/slurm/site.env   # edit partition, account, modules, paths
bash benchmarks/slurm/submit_scaling_sweep.sh 2 4 8 16            # NCCL + OSU across N nodes
sbatch benchmarks/slurm/p2p_intra_node.sbatch
sbatch benchmarks/slurm/ib_perftest.sbatch
sbatch benchmarks/slurm/inference_tp_pp.sbatch
```

External tools expected (build once, paths in `site.env`): `nccl-tests`
(https://github.com/NVIDIA/nccl-tests), OSU micro-benchmarks
(https://mvapich.cse.ohio-state.edu/benchmarks/), `perftest` (usually packaged with
MLNX_OFED), `nvbandwidth` (https://github.com/NVIDIA/nvbandwidth), vLLM (pip or container).
Parsers for their outputs are in `rentscale.benchparse` (`rentscale parse-nccl FILE`, …).
