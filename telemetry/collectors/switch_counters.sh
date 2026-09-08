#!/usr/bin/env bash
# Switch-port byte counters for the rack / pod boundaries (run by someone with fabric
# management access — CARC ops — or from a node with umad access for InfiniBand).
#
#   InfiniBand:  bash switch_counters.sh ib  OUT.csv INTERVAL  "LID:PORT LID:PORT ..."
#                (perfquery -x gives 64-bit extended counters; PortXmitData in 4-octet units)
#   Ethernet:    SNMP_COMMUNITY=public bash switch_counters.sh snmp OUT.csv INTERVAL "switch1 switch2"
#                (IF-MIB::ifHCInOctets / ifHCOutOctets per ifIndex)
#
# Get LID:PORT pairs for leaf uplinks from `iblinkinfo` (hardware/inventory/fabric_discover.sh).
# Reads counters only. Stops on SIGTERM/SIGINT.
set -u
MODE=${1:?ib|snmp}; OUT=${2:?out.csv}; INTERVAL=${3:-1}; TARGETS=${4:?targets}
trap 'exit 0' TERM INT
case "$MODE" in
  ib)
    command -v perfquery >/dev/null || { echo "perfquery not found" >&2; exit 1; }
    echo "t_unix,lid,port,xmit_data_4B,rcv_data_4B,xmit_pkts,rcv_pkts" >"$OUT"
    while :; do
      t=$(date +%s.%N)
      for tp in $TARGETS; do
        lid=${tp%%:*}; port=${tp##*:}
        perfquery -x "$lid" "$port" 2>/dev/null | awk -v t="$t" -v l="$lid" -v p="$port" '
          /PortXmitData/ {xd=$2} /PortRcvData/ {rd=$2} /PortXmitPkts/ {xp=$2} /PortRcvPkts/ {rp=$2}
          END {gsub(/\./,"",xd); gsub(/\./,"",rd); gsub(/\./,"",xp); gsub(/\./,"",rp); printf "%s,%s,%s,%s,%s,%s,%s\n", t, l, p, xd, rd, xp, rp}' >>"$OUT"
      done
      sleep "$INTERVAL"
    done ;;
  snmp)
    command -v snmpwalk >/dev/null || { echo "snmpwalk not found" >&2; exit 1; }
    : "${SNMP_COMMUNITY:?set SNMP_COMMUNITY}"
    echo "t_unix,switch,ifindex,direction,octets" >"$OUT"
    while :; do
      t=$(date +%s.%N)
      for sw in $TARGETS; do
        snmpwalk -v2c -c "$SNMP_COMMUNITY" -Oqv -On "$sw" IF-MIB::ifHCInOctets 2>/dev/null | nl -ba | awk -v t="$t" -v s="$sw" '{printf "%s,%s,%s,in,%s\n", t, s, $1, $2}' >>"$OUT"
        snmpwalk -v2c -c "$SNMP_COMMUNITY" -Oqv -On "$sw" IF-MIB::ifHCOutOctets 2>/dev/null | nl -ba | awk -v t="$t" -v s="$sw" '{printf "%s,%s,%s,out,%s\n", t, s, $1, $2}' >>"$OUT"
      done
      sleep "$INTERVAL"
    done ;;
  *) echo "mode must be ib or snmp" >&2; exit 1 ;;
esac
