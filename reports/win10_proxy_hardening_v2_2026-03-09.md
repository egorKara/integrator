# Win10 Proxy Hardening v2 — 2026-03-09

## Что внедрено
- Пароль прокси убран из `.env.local` (`PROXY_PASS=` пустой).
- Добавлен `PROXY_CRED_TARGET=integrator/proxy/us`.
- Реализовано чтение секрета из Windows Credential Manager:
  - `C:\integrator\proxy_credman.ps1`
- Добавлен bootstrap записи секрета в Credential Manager:
  - `C:\integrator\set_proxy_secret_credman.ps1`
- Обновлён apply/verify:
  - `C:\integrator\set_us_proxy_and_test.ps1`
  - `C:\integrator\run_win10_proxy_pipeline.ps1`
- В pipeline включена очистка user env `HTTP_PROXY/HTTPS_PROXY` перед применением.

## Проверки
- Синтаксис всех новых/обновлённых скриптов: `PS_PARSE_OK`.
- Проверка CredMan target: сейчас `CRED_NOT_FOUND`, поэтому pipeline ожидаемо останавливается с `Credential lookup failed`.
- Поиск утечки старого секрета в `.ps1/.md/.env.local`: не найден.

## Как запустить теперь
1. Сохранить пароль в Credential Manager:
   - `powershell -ExecutionPolicy Bypass -File C:\integrator\set_proxy_secret_credman.ps1`
2. Запустить one-command pipeline:
   - `powershell -ExecutionPolicy Bypass -File C:\integrator\run_win10_proxy_pipeline.ps1`

## Восстановление интернета
- `powershell -ExecutionPolicy Bypass -File C:\integrator\restore_win10_inet_access.ps1 -BackupDir "<путь_к_proxy_backup_...>"`
