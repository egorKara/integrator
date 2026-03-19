#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] Обновление базовых пакетов"
sudo apt update
sudo apt upgrade -y

echo "[2/7] Установка сервисных инструментов"
sudo apt install -y htop lm-sensors smartmontools acpid psmisc

echo "[3/7] Проверка места на диске"
df -hT

echo "[4/7] Включение периодического trim (SSD)"
sudo systemctl enable --now fstrim.timer

echo "[5/7] Проверка файловой системы на ошибки (без правки)"
ROOT_DEV="$(findmnt -no SOURCE /)"
sudo fsck -N "$ROOT_DEV" || true

echo "[6/7] Проверка критических ошибок ядра текущей загрузки"
journalctl -k -p 0..3 -b --no-pager | tail -n 120 || true

echo "[7/7] Готово. Рекомендуется перезагрузка"
echo "sudo reboot"
