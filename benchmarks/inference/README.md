# inference/

- `run_vllm_server.sh MODEL TP PORT OUT_DIR` — OpenAI-compatible vLLM server, TP GPUs.
- `load_generator.py` — open-loop Poisson load with fixed / exponential / Pareto prompt and
  output lengths; per-request CSV with token counts; `--dry-run` prints the schedule.
- The Slurm driver is `../slurm/inference_tp_pp.sbatch`.

Per-token normalization: join the collectors' rates (`rentscale rates`) with the load
generator's `t_send_mono` / `completion_tokens` over each rate window; bytes crossing each
boundary ÷ tokens generated in the window = `B_ℓ` (Topic 02).

Predicted magnitudes for a Llama-70B-class model with TP = 8 in bf16: ≈ 4.6 MB/token/GPU
over NVLink; ≈ 16 KB/token per pipeline boundary over InfiniBand.
