#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "[ERROR] Строка $LINENO: команда завершилась с ошибкой"; exit 1' ERR

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "Нет команды: $1"; exit 1; }; }

need_cmd sudo
need_cmd systemctl
need_cmd awk
need_cmd ip
need_cmd ss

echo "[1/12] Определяю целевого пользователя..."
U="${SUDO_USER:-}"
if [[ -z "${U}" ]]; then
  U="$(logname 2>/dev/null || true)"
fi
if [[ -z "${U}" ]] || ! id "${U}" >/dev/null 2>&1; then
  U="$(id -un)"
fi
echo "USER=${U}"

echo "[2/12] Устанавливаю OpenSSH Server (если не установлен)..."
if command -v dpkg >/dev/null 2>&1 && dpkg -s openssh-server >/dev/null 2>&1; then
  echo "openssh-server уже установлен"
else
  if command -v apt >/dev/null 2>&1; then
    sudo apt update
    sudo apt install -y openssh-server
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y openssh-server
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm openssh
  else
    echo "Не найден поддерживаемый пакетный менеджер (apt/dnf/pacman)"
    exit 1
  fi
fi

echo "[3/12] Делаю бэкап SSH-конфигов..."
TS="$(date +%Y%m%d_%H%M%S)"
BK="/etc/ssh/backup_${TS}"
sudo mkdir -p "${BK}"
sudo cp -a /etc/ssh/sshd_config "${BK}/sshd_config.bak" || true
sudo cp -a /etc/ssh/sshd_config.d "${BK}/sshd_config.d.bak" || true
echo "BACKUP=${BK}"

echo "[4/12] Пишу минимально безопасный рабочий конфиг..."
sudo install -d -m 755 /etc/ssh/sshd_config.d
sudo tee /etc/ssh/sshd_config.d/99-stealth-nexus.conf >/dev/null <<'CFG'
PasswordAuthentication yes
KbdInteractiveAuthentication yes
PubkeyAuthentication yes
UsePAM yes
PermitRootLogin no
ChallengeResponseAuthentication no
X11Forwarding no
CFG

echo "[5/12] Проверяю синтаксис sshd..."
sudo sshd -t

echo "[6/12] Включаю и перезапускаю корректный unit..."
if systemctl list-unit-files --type=service | grep -q '^ssh\.service'; then
  UNIT="ssh.service"
  sudo systemctl enable --now ssh.service
  sudo systemctl restart ssh.service
elif systemctl list-unit-files --type=service | grep -q '^sshd\.service'; then
  UNIT="sshd.service"
  sudo systemctl enable --now sshd.service
  sudo systemctl restart sshd.service
elif systemctl list-unit-files --type=socket | grep -q '^ssh\.socket'; then
  UNIT="ssh.socket"
  sudo systemctl enable --now ssh.socket
  sudo systemctl restart ssh.socket
else
  echo "Не найдено ssh.service / sshd.service / ssh.socket"
  exit 1
fi
echo "UNIT=${UNIT}"

echo "[7/12] Проверяю, что SSH реально слушает порт 22..."
if ! ss -ltn | awk '{print $4}' | grep -qE '(^|\]):22$|:22$'; then
  echo "Порт 22 не слушается после старта SSH"
  exit 1
fi

echo "[8/12] Открываю порт 22 в ufw (только если ufw активен)..."
if command -v ufw >/dev/null 2>&1; then
  if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 22/tcp
  else
    echo "ufw не активен, шаг пропущен"
  fi
fi

echo "[9/12] Разблокирую пользователя и задаю новый пароль..."
sudo usermod -U "${U}" || true
if command -v chsh >/dev/null 2>&1; then
  sudo chsh -s /bin/bash "${U}" || true
fi
echo "Сейчас задай НОВЫЙ пароль для пользователя ${U}:"
sudo passwd "${U}"

echo "[10/12] Проверяю эффективные параметры SSH..."
EFFECTIVE="$(sudo sshd -T)"
echo "${EFFECTIVE}" | grep -q '^passwordauthentication yes$' || { echo "passwordauthentication не включён"; exit 1; }
echo "${EFFECTIVE}" | grep -q '^kbdinteractiveauthentication yes$' || { echo "kbdinteractiveauthentication не включён"; exit 1; }
echo "${EFFECTIVE}" | grep -q '^usepam yes$' || { echo "usepam не включён"; exit 1; }

echo "[11/12] Проверяю статус пользователя..."
PASS_STATE="$(sudo passwd -S "${U}" | awk '{print $2}')"
if [[ "${PASS_STATE}" = "L" ]]; then
  echo "Пользователь ${U} заблокирован (passwd -S=${PASS_STATE})"
  exit 1
fi

echo "[12/12] Вычисляю IP и печатаю готовую команду..."
IP="$(ip -4 route get 1.1.1.1 | awk '/src/ {print $7; exit}')"
if [[ -z "${IP}" ]]; then
  IP="$(hostname -I | awk '{print $1}')"
fi
[[ -n "${IP}" ]] || { echo "Не удалось определить IP"; exit 1; }

CMD="ssh -F NUL -o PreferredAuthentications=password -o PubkeyAuthentication=no ${U}@${IP}"
echo "${CMD}" | tee "${HOME}/ssh_connect_cmd.txt"

echo
echo "ГОТОВО"
echo "Команда подключения сохранена в: ${HOME}/ssh_connect_cmd.txt"
echo "Подключение с Windows:"
echo "${CMD}"
echo
read -rp "Нажми Enter для выхода..."
