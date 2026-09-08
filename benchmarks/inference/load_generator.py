#!/usr/bin/env python3
"""Open-loop load generator for an OpenAI-compatible completions endpoint (stdlib only).

Requests arrive as a Poisson process at --rate per second; prompt and output lengths are
drawn from --prompt-len-dist / --output-len-dist (fixed, exponential, or pareto with tail
index --pareto-alpha — the heavy-tail knob for the Hurst experiment, Topic 03). Each
request's send time, latency, and token counts (from the server's `usage`) go to a CSV so
counters can be normalized per token.

    python load_generator.py --url http://127.0.0.1:8000 --model /path/model --rate 4 --duration 300 \
        --prompt-len 512 --output-len 128 --output-len-dist pareto --pareto-alpha 1.5 --out load.csv

`--dry-run` prints the schedule without sending anything.
"""
import argparse
import csv
import json
import random
import sys
import threading
import time
import urllib.error
import urllib.request

FILLER = ("the quick brown fox jumps over the lazy dog and keeps running through the fields "
          "under a wide blue sky while counting stones along the river bank ").split()


def sample_length(dist, mean, rng, alpha=1.5, minimum=1, maximum=None):
    """Draw one length: 'fixed' -> mean; 'exponential' -> Exp(mean); 'pareto' -> Pareto
    with tail index alpha and the same mean (x_min = mean * (alpha-1)/alpha), alpha > 1."""
    if dist == "fixed":
        v = mean
    elif dist == "exponential":
        v = rng.expovariate(1.0 / mean)
    elif dist == "pareto":
        if alpha <= 1:
            raise ValueError("pareto alpha must exceed 1 for a finite mean")
        xmin = mean * (alpha - 1.0) / alpha
        v = xmin / (1.0 - rng.random()) ** (1.0 / alpha)
    else:
        raise ValueError("unknown distribution %r" % dist)
    v = max(minimum, int(round(v)))
    return min(v, maximum) if maximum else v


def poisson_schedule(rate, duration, rng):
    """Arrival offsets (seconds) of a Poisson process with the given rate over duration."""
    t = 0.0
    out = []
    while True:
        t += rng.expovariate(rate)
        if t > duration:
            break
        out.append(t)
    return out


def make_prompt(n_words, rng):
    return " ".join(rng.choice(FILLER) for _ in range(n_words))


def send_one(url, model, prompt, max_tokens, timeout):
    body = json.dumps({"model": model, "prompt": prompt, "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/v1/completions", data=body, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        usage = data.get("usage", {})
        return {"ok": 1, "latency_s": time.monotonic() - t0, "prompt_tokens": usage.get("prompt_tokens", ""),
                "completion_tokens": usage.get("completion_tokens", ""), "error": ""}
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError) as e:
        return {"ok": 0, "latency_s": time.monotonic() - t0, "prompt_tokens": "", "completion_tokens": "", "error": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--model", required=True)
    ap.add_argument("--rate", type=float, default=1.0, help="mean requests per second")
    ap.add_argument("--duration", type=float, default=60.0, help="seconds of arrivals")
    ap.add_argument("--prompt-len", type=int, default=256, help="mean prompt length (words)")
    ap.add_argument("--prompt-len-dist", choices=["fixed", "exponential", "pareto"], default="fixed")
    ap.add_argument("--output-len", type=int, default=128, help="mean max_tokens")
    ap.add_argument("--output-len-dist", choices=["fixed", "exponential", "pareto"], default="fixed")
    ap.add_argument("--pareto-alpha", type=float, default=1.5)
    ap.add_argument("--max-output-len", type=int, default=2048)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="-")
    ap.add_argument("--summary")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    schedule = poisson_schedule(a.rate, a.duration, rng)
    plan = []
    for i, t in enumerate(schedule):
        plan.append((i, t, sample_length(a.prompt_len_dist, a.prompt_len, rng, a.pareto_alpha, 1, 4096),
                     sample_length(a.output_len_dist, a.output_len, rng, a.pareto_alpha, 1, a.max_output_len)))
    if a.dry_run:
        print("id,t_offset_s,prompt_words,max_tokens")
        for i, t, pl, ol in plan:
            print("%d,%.3f,%d,%d" % (i, t, pl, ol))
        return 0

    fh = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(fh)
    w.writerow(["id", "t_send_unix", "t_send_mono", "t_offset_s", "prompt_words", "max_tokens", "ok", "latency_s",
                "prompt_tokens", "completion_tokens", "error"])
    lock = threading.Lock()
    results = []

    def worker(i, t_off, pl, ol):
        prompt = make_prompt(pl, rng)
        tu, tm = time.time(), time.monotonic()
        r = send_one(a.url, a.model, prompt, ol, a.timeout)
        with lock:
            w.writerow([i, "%.6f" % tu, "%.6f" % tm, "%.3f" % t_off, pl, ol, r["ok"], "%.4f" % r["latency_s"],
                        r["prompt_tokens"], r["completion_tokens"], r["error"]])
            fh.flush()
            results.append(r)

    t0 = time.monotonic()
    threads = []
    for i, t_off, pl, ol in plan:
        delay = t0 + t_off - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        th = threading.Thread(target=worker, args=(i, t_off, pl, ol), daemon=True)
        th.start()
        threads.append(th)
    for th in threads:
        th.join()
    elapsed = time.monotonic() - t0
    if fh is not sys.stdout:
        fh.close()
    ok = [r for r in results if r["ok"]]
    comp = sum(int(r["completion_tokens"] or 0) for r in ok)
    prom = sum(int(r["prompt_tokens"] or 0) for r in ok)
    summary = {"requests": len(plan), "ok": len(ok), "elapsed_s": elapsed, "rate_target": a.rate,
               "rate_achieved": len(ok) / elapsed if elapsed else 0.0, "prompt_tokens": prom,
               "completion_tokens": comp, "tokens_per_s": (prom + comp) / elapsed if elapsed else 0.0,
               "mean_latency_s": sum(r["latency_s"] for r in ok) / len(ok) if ok else None,
               "prompt_len_dist": a.prompt_len_dist, "output_len_dist": a.output_len_dist, "pareto_alpha": a.pareto_alpha}
    text = json.dumps(summary, indent=2)
    if a.summary:
        with open(a.summary, "w") as sfh:
            sfh.write(text)
    sys.stderr.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
