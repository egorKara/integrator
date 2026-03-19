#!/usr/bin/env bash
set -euo pipefail

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo not found"
  exit 1
fi

U="${SUDO_USER:-}"
if [ -z "$U" ]; then
  U="$(logname 2>/dev/null || true)"
fi
if [ -z "$U" ] || ! id "$U" >/dev/null 2>&1; then
  U="$(id -un)"
fi

echo "Detected user: $U"

if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y openssh-server
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y openssh-server
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -Sy --noconfirm openssh
else
  echo "Supported package manager not found"
  exit 1
fi

sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-stealth-nexus.conf >/dev/null <<'CFG'
PasswordAuthentication yes
PermitRootLogin no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
CFG

if systemctl list-unit-files --type=service | grep -q '^ssh\.service'; then
  sudo systemctl enable --now ssh
  sudo systemctl restart ssh
elif systemctl list-unit-files --type=service | grep -q '^sshd\.service'; then
  sudo systemctl enable --now sshd
  sudo systemctl restart sshd
elif systemctl list-unit-files --type=socket | grep -q '^ssh\.socket'; then
  sudo systemctl enable --now ssh.socket
  sudo systemctl restart ssh.socket
else
  echo "No ssh unit found (ssh.service/sshd.service/ssh.socket)"
  exit 1
fi

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 22/tcp || true
fi

echo "Set password for user $U"
sudo passwd "$U"

IP="$(ip -4 route get 1.1.1.1 | awk '/src/ {print $7; exit}')"
if [ -z "${IP:-}" ]; then
  IP="$(hostname -I | awk '{print $1}')"
fi

OUT="$HOME/ssh_connect_cmd.txt"
echo "ssh $U@$IP" | tee "$OUT"

echo
echo "DONE"
echo "Connection command saved to: $OUT"
echo "Use on Windows PowerShell:"
echo "ssh $U@$IP"
echo
read -rp "Press Enter to close..."
