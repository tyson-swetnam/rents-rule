#!/usr/bin/env bash
# InfiniBand fabric discovery for the census (needs read access to /dev/infiniband/umad*,
# i.e. root or the `rdma` group; otherwise ask CARC ops to run it on the SM host):
#   bash hardware/inventory/fabric_discover.sh [OUT_ROOT] [CA] [PORT]
# Also dumps LLDP neighbours for Ethernet if lldpctl exists. Reads only; no fabric changes.
set -u
OUT="${1:-runs/census}/fabric"
CA=${2:-}
PORT=${3:-}
mkdir -p "$OUT"
have() { command -v "$1" >/dev/null 2>&1; }
opts=()
[ -n "$CA" ] && opts+=(-C "$CA")
[ -n "$PORT" ] && opts+=(-P "$PORT")

if ls /dev/infiniband/umad* >/dev/null 2>&1; then
  for f in /dev/infiniband/umad*; do [ -r "$f" ] || echo "WARN: $f not readable by $(id -un); ibnetdiscover will fail" >&2; done
else
  echo "WARN: no /dev/infiniband/umad* device on this host" >&2
fi

run() { local f="$OUT/$1"; shift; if have "$1"; then "$@" >"$f" 2>"$f.err" || echo "WARN: $* exited $? (see $f.err)" >&2; [ -s "$f.err" ] || rm -f "$f.err"; else echo "SKIP: $1 not found" >&2; echo "$1" >>"$OUT/missing_tools.txt"; fi; }

run ibnetdiscover.txt       ibnetdiscover "${opts[@]}"
run ibnetdiscover_ports.txt ibnetdiscover -p "${opts[@]}"
run ibswitches.txt          ibswitches "${opts[@]}"
run ibhosts.txt             ibhosts "${opts[@]}"
run iblinkinfo.txt          iblinkinfo "${opts[@]}"
run lldp_neighbors.txt      lldpctl
{ echo "date_utc=$(date -u +%FT%TZ)"; echo "host=$(hostname)"; echo "ca=$CA port=$PORT"; } >"$OUT/meta.txt"
echo "wrote $OUT:"; ls -1 "$OUT"
echo "next: rentscale fabric $OUT/ibnetdiscover.txt"
