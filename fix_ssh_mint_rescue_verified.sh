#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "[ERROR] line $LINENO"; exit 1' ERR

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1"; exit 1; }; }

need sudo
need systemctl
need awk
need ip
need ss
need grep
need ssh

echo "[1/11] install openssh-server + sshpass if needed"
if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y openssh-server sshpass
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y openssh-server sshpass
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -Sy --noconfirm openssh sshpass
else
  echo "unsupported package manager"
  exit 1
fi

echo "[2/11] create/prepare rescue user"
RESCUE_USER="snxrescue"
if ! id "${RESCUE_USER}" >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash "${RESCUE_USER}"
fi
sudo chsh -s /bin/bash "${RESCUE_USER}" || true

echo "[3/11] set deterministic temporary password"
RESCUE_PASS='SnxTemp!20260308'
sudo chpasswd <<<"${RESCUE_USER}:${RESCUE_PASS}"

echo "[4/11] write sshd config"
sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-snx-rescue.conf >/dev/null <<'CFG'
PasswordAuthentication yes
KbdInteractiveAuthentication yes
UsePAM yes
PubkeyAuthentication yes
PermitRootLogin no
ChallengeResponseAuthentication no
X11Forwarding no
CFG

echo "[5/11] validate sshd config"
sudo sshd -t

echo "[6/11] restart ssh daemon/socket"
if systemctl list-unit-files --type=service | grep -q '^ssh\.service'; then
  sudo systemctl enable --now ssh.service
  sudo systemctl restart ssh.service
elif systemctl list-unit-files --type=service | grep -q '^sshd\.service'; then
  sudo systemctl enable --now sshd.service
  sudo systemctl restart sshd.service
elif systemctl list-unit-files --type=socket | grep -q '^ssh\.socket'; then
  sudo systemctl enable --now ssh.socket
  sudo systemctl restart ssh.socket
else
  echo "no ssh unit found"
  exit 1
fi

echo "[7/11] verify port 22 is listening"
ss -ltn | awk '{print $4}' | grep -qE '(^|\]):22$|:22$'

echo "[8/11] verify effective sshd options"
E="$(sudo sshd -T)"
echo "${E}" | grep -q '^passwordauthentication yes$'
echo "${E}" | grep -q '^kbdinteractiveauthentication yes$'
echo "${E}" | grep -q '^usepam yes$'

echo "[9/11] open firewall if active"
if command -v ufw >/dev/null 2>&1; then
  if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 22/tcp
  fi
fi

echo "[10/11] end-to-end local ssh login test"
need sshpass
sshpass -p "${RESCUE_PASS}" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "${RESCUE_USER}@127.0.0.1" "id -un" | grep -qx "${RESCUE_USER}"

echo "[11/11] print ready-to-use connection data"
IP="$(ip -4 route get 1.1.1.1 | awk '/src/ {print $7; exit}')"
if [[ -z "${IP}" ]]; then
  IP="$(hostname -I | awk '{print $1}')"
fi
[[ -n "${IP}" ]] || { echo "ip detect failed"; exit 1; }

OUT="${HOME}/snx_ssh_ready.txt"
{
  echo "SSH_USER=${RESCUE_USER}"
  echo "SSH_PASS=${RESCUE_PASS}"
  echo "SSH_IP=${IP}"
  echo "SSH_CMD=ssh -F NUL -o PreferredAuthentications=password -o PubkeyAuthentication=no ${RESCUE_USER}@${IP}"
} | tee "${OUT}"

echo "READY_FILE=${OUT}"
