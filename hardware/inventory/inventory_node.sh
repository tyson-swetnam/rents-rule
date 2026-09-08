#!/usr/bin/env bash
# Inventory one node for the Rent census: CPUs, GPUs, NVLink/PCIe topology, HCAs, NICs.
#
#   bash hardware/inventory/inventory_node.sh [OUT_ROOT]        (default runs/census)
#   srun -p <partition> -N1 -c1 -t 10 bash hardware/inventory/inventory_node.sh runs/census
#
# Writes OUT_ROOT/<hostname>/... . Safe on nodes without GPUs, InfiniBand, or root: every
# tool is optional and anything missing is listed in missing_tools.txt. Reads only.
set -u
OUT_ROOT=${1:-runs/census}
HOST=$(hostname -s 2>/dev/null || hostname)
OUT="$OUT_ROOT/$HOST"
mkdir -p "$OUT"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT/inventory.log"; }
have() { command -v "$1" >/dev/null 2>&1; }
# run <outfile> <cmd...>: capture stdout; stderr to <outfile>.err (removed if empty)
run() {
  local f="$OUT/$1"; shift
  if have "$1"; then
    "$@" >"$f" 2>"$f.err" || log "WARN: '$*' exited $? (see $(basename "$f").err)"
    [ -s "$f.err" ] || rm -f "$f.err"
  else
    log "SKIP: $1 not found"; echo "$1" >>"$OUT/missing_tools.txt"
  fi
}

{
  echo "hostname=$HOST"
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "kernel=$(uname -r)"
  echo "user=$(id -un)"
  echo "slurm_job_id=${SLURM_JOB_ID:-}"
  echo "slurm_nodelist=${SLURM_JOB_NODELIST:-}"
  echo "slurm_partition=${SLURM_JOB_PARTITION:-}"
  echo "git_sha=$(git -C "$(dirname "$0")" rev-parse --short HEAD 2>/dev/null || echo unknown)"
} >"$OUT/meta.txt"

# --- CPU / memory / OS
run lscpu.json        lscpu -J
run lscpu.txt         lscpu
run numactl.txt       numactl -H
run meminfo.txt       cat /proc/meminfo
run os-release.txt    cat /etc/os-release
run lstopo.xml        lstopo-no-graphics --of xml
run lspci.txt         lspci -vv
run lspci_tree.txt    lspci -tv
run ip_link.json      ip -j link
run ip_link.txt       ip link

# --- NVIDIA GPUs
run nvidia-smi_query.csv nvidia-smi --query-gpu=index,name,uuid,pci.bus_id,pcie.link.gen.max,pcie.link.gen.current,pcie.link.width.max,pcie.link.width.current,memory.total,power.limit,driver_version --format=csv
run nvidia-smi_topo.txt   nvidia-smi topo -m
run nvidia-smi_nvlink_status.txt nvidia-smi nvlink -s
run nvidia-smi_q.txt      nvidia-smi -q
# --- AMD GPUs
run rocm-smi.txt      rocm-smi --showproductname --showbus --showtopo

# --- InfiniBand / RoCE
run ibstat.txt        ibstat
run ibv_devinfo.txt   ibv_devinfo -v
run ibdev2netdev.txt  ibdev2netdev -v
: >"$OUT/ib_sysfs.txt"
for p in /sys/class/infiniband/*/ports/*; do
  [ -d "$p" ] || continue
  dev=$(basename "$(dirname "$(dirname "$p")")"); port=$(basename "$p")
  {
    echo "device=$dev port=$port"
    for f in state phys_state rate link_layer; do
      printf '%s=%s\n' "$f" "$(cat "$p/$f" 2>/dev/null | tr -d '\n')"
    done
  } >>"$OUT/ib_sysfs.txt"
done

# --- Ethernet
if have ethtool; then
  for i in $(ls /sys/class/net 2>/dev/null | grep -v -E '^(lo|docker.*|veth.*|virbr.*|br-.*|cali.*|flannel.*|tun.*)$'); do
    ethtool "$i" >"$OUT/ethtool_$i.txt" 2>/dev/null || true
    ethtool -i "$i" >"$OUT/ethtool_i_$i.txt" 2>/dev/null || true
  done
else
  log "SKIP: ethtool not found"; echo ethtool >>"$OUT/missing_tools.txt"
fi

# --- DMI (root only)
if [ "$(id -u)" = "0" ]; then run dmidecode.txt dmidecode; else log "SKIP: dmidecode (needs root)"; fi

log "done -> $OUT"
