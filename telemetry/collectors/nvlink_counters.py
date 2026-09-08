#!/usr/bin/env python3
"""GPU interconnect and utilization telemetry (stdlib only).

Backends:
  dcgmi       (preferred) runs `dcgmi dmon -e <fields> -d <ms>` and re-emits rows as CSV
              with timestamps. Default fields: 1011 NVLink TX bytes, 1012 NVLink RX bytes,
              1009 PCIe TX bytes, 1010 PCIe RX bytes, 1001 graphics engine active,
              1004 tensor pipe active, 1005 DRAM active, 155 power (W). Byte fields are
              rates over the sample interval as reported by DCGM.
  nvidia-smi  polls `nvidia-smi nvlink -gt d` (cumulative KiB per link per direction) and
              `nvidia-smi --query-gpu=utilization.gpu,power.draw`; parse with
              rentscale.counters.parse_nvidia_smi_nvlink_throughput.

    python nvlink_counters.py --backend dcgmi --interval 0.1 --out gpu_dcgm.csv
    python nvlink_counters.py --backend nvidia-smi --interval 0.5 --out gpu_nvsmi.txt
"""
import argparse
import csv
import shutil
import signal
import socket
import subprocess
import sys
import time

DEFAULT_FIELDS = "1011,1012,1009,1010,1001,1004,1005,155"
_stop = False


def _on_signal(signum, frame):
    global _stop
    _stop = True


def run_dcgmi(a):
    if not shutil.which("dcgmi"):
        sys.stderr.write("nvlink_counters: dcgmi not found; try --backend nvidia-smi\n")
        return 1
    ms = max(100, int(a.interval * 1000))  # dcgmi minimum is 100 ms
    cmd = ["dcgmi", "dmon", "-e", a.fields, "-d", str(ms)]
    if a.duration:
        cmd += ["-c", str(int(a.duration / (ms / 1000.0)))]
    host = socket.gethostname().split(".")[0]
    fh = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(fh)
    header = None
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    try:
        for line in proc.stdout:
            s = line.strip()
            if _stop:
                break
            if s.startswith("#Entity") or s.startswith("# Entity"):
                header = s.lstrip("#").split()[1:]
                w.writerow(["t_unix", "t_mono", "host", "entity", "id"] + header)
                continue
            if not s or s == "ID" or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) >= 2 and parts[0] in ("GPU", "Switch", "CPU"):
                w.writerow([f"{time.time():.6f}", f"{time.monotonic():.6f}", host, parts[0], parts[1]] + parts[2:])
                fh.flush()
    finally:
        if proc.poll() is None:
            proc.terminate()
        if fh is not sys.stdout:
            fh.close()
    return 0


def run_nvidia_smi(a):
    if not shutil.which("nvidia-smi"):
        sys.stderr.write("nvlink_counters: nvidia-smi not found; exiting\n")
        return 0
    fh = sys.stdout if a.out == "-" else open(a.out, "w")
    t0 = time.monotonic()
    next_t = t0
    try:
        while not _stop:
            now_m, now_u = time.monotonic(), time.time()
            nv = subprocess.run(["nvidia-smi", "nvlink", "-gt", "d"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout
            ut = subprocess.run(["nvidia-smi", "--query-gpu=index,utilization.gpu,power.draw,pcie.link.gen.current,pcie.link.width.current", "--format=csv,noheader,nounits"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True).stdout
            fh.write("=== SAMPLE t_unix=%.6f t_mono=%.6f\n%s--- util index,util_pct,power_w,pcie_gen,pcie_width\n%s" % (now_u, now_m, nv, ut))
            fh.flush()
            if a.duration and (now_m - t0) >= a.duration:
                break
            next_t += a.interval
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.monotonic()
    finally:
        if fh is not sys.stdout:
            fh.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=["dcgmi", "nvidia-smi"], default="dcgmi")
    ap.add_argument("--fields", default=DEFAULT_FIELDS, help="DCGM field ids for the dcgmi backend")
    ap.add_argument("--interval", type=float, default=0.1)
    ap.add_argument("--duration", type=float, default=0.0)
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    return run_dcgmi(a) if a.backend == "dcgmi" else run_nvidia_smi(a)


if __name__ == "__main__":
    sys.exit(main())
