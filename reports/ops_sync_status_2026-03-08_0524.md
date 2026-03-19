# Ops Sync Status — 2026-03-08 05:24

- Ноутбук в LAN доступен по SSH/22: `192.168.31.124`.
- `.env` синхронизирован под нового пользователя Mint:
  - `CLIENT_USER=oem`
  - `ZAPRET_SSH_USER=oem`
- Проверка SSH с хоста:
  - `oem@192.168.31.124: Permission denied (publickey,password,keyboard-interactive).`
- Проверка provider auth:
  - `AUTH=FAIL`.
- Повторные client apply/verify:
  - `WinError 10013` (без изменений).

## Новые артефакты
- `C:\integrator\reports\laptop_access_probe_active_20260308_052227.log`
- `C:\integrator\reports\ssh_connectivity_20260308_052316.log`
- `C:\integrator\reports\client_chain_apply_20260308_052316.log`
- `C:\integrator\reports\client_chain_verify_20260308_052316.log`
- `C:\integrator\reports\proxy_auth_check_20260308_052354.log`
