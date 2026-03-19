# US TUN Mode (Windows)

## Предпосылки

- Настроен `.env.local` с полями `PROXY_IP`, `PROXY_PORT`, `PROXY_USER`, `PROXY_CRED_TARGET`.
- В Credential Manager есть секрет для `PROXY_CRED_TARGET`.
- Установлен `sing-box` по пути `C:\integrator\bin\sing-box.exe`.
- Hiddify должен быть остановлен для целевого режима без туннеля Hiddify.

## Включение

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\us_tun_on.ps1 -ForceStopHiddify
```

## Статус

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\us_tun_status.ps1
```

## Проверка egress

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\us_tun_verify_egress.ps1
```

## Выключение и rollback

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\us_tun_off.ps1
```

## Логи

- `C:\integrator\reports\us_tun_on_*.log`
- `C:\integrator\reports\us_tun_off_*.log`
- `C:\integrator\reports\us_tun_verify_*.log`
- `C:\integrator\reports\us_tun_state.json`

