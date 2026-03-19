#!/usr/bin/env bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="$HOME/mint_freeze_snapshot_$TS"
mkdir -p "$OUT_DIR"

run_safe() {
  local name="$1"
  shift
  {
    echo "### $name"
    "$@"
  } >"$OUT_DIR/$name.txt" 2>&1 || true
}

run_safe uname uname -a
run_safe os_release cat /etc/os-release
run_safe uptime uptime
run_safe who who -a
run_safe last_boot last -x | head -n 60
run_safe memory free -h
run_safe vmstat vmstat 1 5
run_safe cpu_top sh -c "ps -eo pid,ppid,comm,%cpu,%mem --sort=-%cpu | head -n 40"
run_safe mem_top sh -c "ps -eo pid,ppid,comm,%mem,%cpu --sort=-%mem | head -n 40"
run_safe iotop_like sh -c "ps -eo pid,ppid,comm,stat,wchan:32 --sort=stat | head -n 80"
run_safe disk df -hT
run_safe block lsblk -f
run_safe mounts mount
run_safe dmesg_tail dmesg -T | tail -n 300
run_safe journal_crit journalctl -p 0..3 -b --no-pager | tail -n 400
run_safe journal_warn journalctl -p 4 -b --no-pager | tail -n 400
run_safe kernel_log journalctl -k -b --no-pager | tail -n 500
run_safe gpu_lspci sh -c "lspci -nnk | grep -EA4 'VGA|3D|Display'"
run_safe thermal sh -c "sensors 2>/dev/null || true"
run_safe network ip -br a
run_safe routes ip route
run_safe ssh_service sh -c "systemctl status ssh --no-pager || systemctl status sshd --no-pager || true"

tar -czf "$HOME/mint_freeze_snapshot_$TS.tar.gz" -C "$HOME" "mint_freeze_snapshot_$TS"
echo "SNAPSHOT_DIR=$OUT_DIR"
echo "SNAPSHOT_TGZ=$HOME/mint_freeze_snapshot_$TS.tar.gz"
