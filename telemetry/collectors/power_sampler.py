#!/usr/bin/env python3
"""Node power sampler (stdlib only): GPU power via nvidia-smi, CPU/package energy via RAPL
(cumulative microjoules in /sys/class/powercap), optional chassis power via
`ipmitool dcmi power reading` (needs BMC access; opt in with --ipmi). Long CSV:
t_unix,t_mono,host,source,id,metric,value,unit.

    python power_sampler.py --interval 1 --out power.csv [--ipmi]
"""
import argparse
import csv
import glob
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

_stop = False


def _on_signal(signum, frame):
    global _stop
    _stop = True


def rapl_domains():
    out = []
    for d in sorted(glob.glob("/sys/class/powercap/*rapl*/**/energy_uj", recursive=True)) + sorted(glob.glob("/sys/class/powercap/*rapl*/energy_uj")):
        base = os.path.dirname(d)
        try:
            with open(os.path.join(base, "name")) as fh:
                name = fh.read().strip()
        except OSError:
            name = os.path.basename(base)
        if os.access(d, os.R_OK):
            out.append((os.path.basename(base) + ":" + name, d))
    return sorted(set(out))


def read_int(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return None


def gpu_power():
    if not shutil.which("nvidia-smi"):
        return []
    r = subprocess.run(["nvidia-smi", "--query-gpu=index,power.draw,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    rows = []
    for line in r.stdout.splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) >= 2:
            rows.append((p[0], "power", p[1], "W"))
            if len(p) >= 3:
                rows.append((p[0], "util", p[2], "%"))
            if len(p) >= 4:
                rows.append((p[0], "temp", p[3], "C"))
    return rows


def ipmi_power():
    if not shutil.which("ipmitool"):
        return None
    r = subprocess.run(["ipmitool", "dcmi", "power", "reading"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    m = re.search(r"Instantaneous power reading:\s*([\d.]+)\s*Watts", r.stdout)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=0.0)
    ap.add_argument("--ipmi", action="store_true", help="also query the BMC (ipmitool dcmi power reading)")
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    host = socket.gethostname().split(".")[0]
    rapl = rapl_domains()
    fh = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(fh)
    w.writerow(["t_unix", "t_mono", "host", "source", "id", "metric", "value", "unit"])
    t0 = time.monotonic()
    next_t = t0
    while not _stop:
        now_m, now_u = time.monotonic(), time.time()
        tu, tm = f"{now_u:.6f}", f"{now_m:.6f}"
        for gid, metric, val, unit in gpu_power():
            w.writerow([tu, tm, host, "nvidia-smi", gid, metric, val, unit])
        for name, path in rapl:
            v = read_int(path)
            if v is not None:
                w.writerow([tu, tm, host, "rapl", name, "energy", v, "uJ"])
        if a.ipmi:
            v = ipmi_power()
            if v is not None:
                w.writerow([tu, tm, host, "ipmi", "chassis", "power", v, "W"])
        fh.flush()
        if a.duration and (now_m - t0) >= a.duration:
            break
        next_t += a.interval
        delay = next_t - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        else:
            next_t = time.monotonic()
    if fh is not sys.stdout:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
