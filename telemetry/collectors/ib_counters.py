#!/usr/bin/env python3
"""Sample InfiniBand port counters from sysfs at a fixed interval -> CSV (stdlib only,
Python 3.6+). Counters are cumulative; `port_xmit_data` / `port_rcv_data` are in units of
4 octets. Convert to rates with `rentscale rates ... --multiplier 4 --group-cols dev,port`.

    python ib_counters.py --interval 0.1 --out ib_counters.csv            # until SIGTERM/SIGINT
    python ib_counters.py --interval 0.1 --duration 600 --devices mlx5_0

Reads byte and packet counts only; never payloads.
"""
import argparse
import csv
import glob
import os
import signal
import socket
import sys
import time

COUNTERS = ["port_xmit_data", "port_rcv_data", "port_xmit_packets", "port_rcv_packets",
            "port_xmit_wait", "port_rcv_errors", "port_xmit_discards"]
_stop = False


def _on_signal(signum, frame):
    global _stop
    _stop = True


def discover(devices=None, active_only=True):
    ports = []
    for pdir in sorted(glob.glob("/sys/class/infiniband/*/ports/*")):
        dev = os.path.basename(os.path.dirname(os.path.dirname(pdir)))
        port = os.path.basename(pdir)
        if devices and dev not in devices:
            continue
        if active_only:
            try:
                with open(os.path.join(pdir, "state")) as fh:
                    if "ACTIVE" not in fh.read():
                        continue
            except OSError:
                continue
        cdir = os.path.join(pdir, "counters")
        avail = [c for c in COUNTERS if os.path.exists(os.path.join(cdir, c))]
        if avail:
            ports.append((dev, port, cdir, avail))
    return ports


def read_counter(path):
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=0.1, help="seconds between samples")
    ap.add_argument("--duration", type=float, default=0.0, help="seconds to run (0 = until signal)")
    ap.add_argument("--devices", nargs="*", help="restrict to these HCA names (e.g. mlx5_0)")
    ap.add_argument("--all-ports", action="store_true", help="include non-ACTIVE ports")
    ap.add_argument("--out", default="-", help="CSV path (default stdout)")
    ap.add_argument("--flush-every", type=int, default=50)
    a = ap.parse_args()

    ports = discover(a.devices, active_only=not a.all_ports)
    if not ports:
        sys.stderr.write("ib_counters: no InfiniBand ports found; exiting\n")
        return 0
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    host = socket.gethostname().split(".")[0]
    fh = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(fh)
    w.writerow(["t_unix", "t_mono", "host", "dev", "port"] + COUNTERS)
    t0 = time.monotonic()
    next_t = t0
    n = 0
    while not _stop:
        now_m = time.monotonic()
        now_u = time.time()
        for dev, port, cdir, avail in ports:
            row = [f"{now_u:.6f}", f"{now_m:.6f}", host, dev, port]
            row += [read_counter(os.path.join(cdir, c)) if c in avail else "" for c in COUNTERS]
            w.writerow(row)
        n += 1
        if n % a.flush_every == 0:
            fh.flush()
        if a.duration and (now_m - t0) >= a.duration:
            break
        next_t += a.interval
        delay = next_t - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        else:  # fell behind; resynchronize instead of bursting
            next_t = time.monotonic()
    fh.flush()
    if fh is not sys.stdout:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
