#!/usr/bin/env python3
"""Sample Ethernet interface counters from /sys/class/net/<iface>/statistics at a fixed
interval -> CSV (stdlib only, Python 3.6+). Cumulative bytes/packets; convert with
`rentscale rates ... --group-cols iface`.

    python nic_counters.py --interval 0.1 --out nic_counters.csv
    python nic_counters.py --ifaces eth0 ens1f0 --duration 600
"""
import argparse
import csv
import os
import signal
import socket
import sys
import time

STATS = ["rx_bytes", "tx_bytes", "rx_packets", "tx_packets", "rx_dropped", "tx_dropped"]
SKIP_PREFIXES = ("lo", "docker", "veth", "virbr", "br-", "cali", "flannel", "tun", "tap")
_stop = False


def _on_signal(signum, frame):
    global _stop
    _stop = True


def discover(ifaces=None):
    out = []
    if not os.path.isdir("/sys/class/net"):
        return out
    for name in sorted(os.listdir("/sys/class/net")):
        if ifaces:
            if name not in ifaces:
                continue
        elif name.startswith(SKIP_PREFIXES):
            continue
        try:
            with open("/sys/class/net/%s/operstate" % name) as fh:
                if fh.read().strip() != "up" and not ifaces:
                    continue
        except OSError:
            continue
        out.append(name)
    return out


def read_stat(iface, stat):
    try:
        with open("/sys/class/net/%s/statistics/%s" % (iface, stat)) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=float, default=0.1)
    ap.add_argument("--duration", type=float, default=0.0)
    ap.add_argument("--ifaces", nargs="*")
    ap.add_argument("--out", default="-")
    ap.add_argument("--flush-every", type=int, default=50)
    a = ap.parse_args()
    ifaces = discover(a.ifaces)
    if not ifaces:
        sys.stderr.write("nic_counters: no interfaces found; exiting\n")
        return 0
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    host = socket.gethostname().split(".")[0]
    fh = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(fh)
    w.writerow(["t_unix", "t_mono", "host", "iface"] + STATS)
    t0 = time.monotonic()
    next_t = t0
    n = 0
    while not _stop:
        now_m, now_u = time.monotonic(), time.time()
        for iface in ifaces:
            w.writerow([f"{now_u:.6f}", f"{now_m:.6f}", host, iface] + [read_stat(iface, s) for s in STATS])
        n += 1
        if n % a.flush_every == 0:
            fh.flush()
        if a.duration and (now_m - t0) >= a.duration:
            break
        next_t += a.interval
        delay = next_t - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        else:
            next_t = time.monotonic()
    fh.flush()
    if fh is not sys.stdout:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
