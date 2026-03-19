#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "[ERROR] line $LINENO"; exit 1' ERR

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1"; exit 1; }; }

need sudo
need systemctl
need awk
need grep
need id
need getent
need ip
need ssh

USER_TO_FIX="${1:-snxrescue}"
if ! id "${USER_TO_FIX}" >/dev/null 2>&1; then
  USER_TO_FIX="oem"
fi
id "${USER_TO_FIX}" >/dev/null 2>&1 || { echo "user not found: snxrescue/oem"; exit 1; }

echo "[1/9] target user: ${USER_TO_FIX}"

echo "[2/9] install sshpass if missing"
if ! command -v sshpass >/dev/null 2>&1; then
  if command -v apt >/dev/null 2>&1; then
    sudo apt update
    sudo apt install -y sshpass
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y sshpass
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm sshpass
  else
    echo "cannot install sshpass automatically"
    exit 1
  fi
fi

echo "[3/9] normalize ssh auth config"
sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-snx-auth-repair.conf >/dev/null <<CFG
PasswordAuthentication yes
KbdInteractiveAuthentication yes
UsePAM yes
PubkeyAuthentication yes
PermitRootLogin no
ChallengeResponseAuthentication no
LogLevel VERBOSE
AllowUsers ${USER_TO_FIX}
CFG

echo "[4/9] validate sshd config"
sudo sshd -t

echo "[5/9] clear auth lockouts"
if command -v faillock >/dev/null 2>&1; then
  sudo faillock --user "${USER_TO_FIX}" --reset || true
fi
if command -v pam_tally2 >/dev/null 2>&1; then
  sudo pam_tally2 --user "${USER_TO_FIX}" --reset || true
fi

echo "[6/9] ensure account is usable"
sudo usermod -U "${USER_TO_FIX}" || true
sudo chage -E -1 "${USER_TO_FIX}" || true
sudo chage -M 99999 "${USER_TO_FIX}" || true
SHELL_PATH="$(getent passwd "${USER_TO_FIX}" | awk -F: '{print $7}')"
if [[ "${SHELL_PATH}" = "/usr/sbin/nologin" || "${SHELL_PATH}" = "/bin/false" ]]; then
  sudo chsh -s /bin/bash "${USER_TO_FIX}"
fi

echo "[7/9] restart ssh unit"
if systemctl list-unit-files --type=service | grep -q '^ssh\.service'; then
  sudo systemctl restart ssh.service
  UNIT="ssh.service"
elif systemctl list-unit-files --type=service | grep -q '^sshd\.service'; then
  sudo systemctl restart sshd.service
  UNIT="sshd.service"
elif systemctl list-unit-files --type=socket | grep -q '^ssh\.socket'; then
  sudo systemctl restart ssh.socket
  UNIT="ssh.socket"
else
  echo "no ssh unit found"
  exit 1
fi

echo "[8/9] verify listener and effective config"
ss -ltn | awk '{print $4}' | grep -qE '(^|\]):22$|:22$'
E="$(sudo sshd -T)"
echo "${E}" | grep -q '^passwordauthentication yes$'
echo "${E}" | grep -q '^kbdinteractiveauthentication yes$'
echo "${E}" | grep -q '^usepam yes$'

echo "[9/9] verify password auth locally"
read -rsp "Enter current password for ${USER_TO_FIX}: " PASS
echo
sshpass -p "${PASS}" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=7 "${USER_TO_FIX}@127.0.0.1" "id -un" | grep -qx "${USER_TO_FIX}"

IP="$(ip -4 route get 1.1.1.1 | awk '/src/ {print $7; exit}')"
[[ -n "${IP}" ]] || IP="$(hostname -I | awk '{print $1}')"
OUT="${HOME}/ssh_fixed_ready.txt"
{
  echo "SSH_USER=${USER_TO_FIX}"
  echo "SSH_IP=${IP}"
  echo "SSH_CMD=ssh -F NUL -o PreferredAuthentications=password -o PubkeyAuthentication=no ${USER_TO_FIX}@${IP}"
} | tee "${OUT}"
echo "READY_FILE=${OUT}"
echo "SSH_UNIT=${UNIT}"
