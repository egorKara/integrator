# Proxy Security Report — 2026-03-09

## Текущее состояние
- Рабочий контур: `socks5h://208.214.160.156:50101`.
- Proxy egress подтверждён: `VERIFY_PROXY_IP=208.214.160.156`, `VERIFY_PROXY_STATUS=OK`.
- Direct-check не является блокирующим: `VERIFY_DIRECT_EXIT=28`.

## Подтверждающие артефакты
- `C:\integrator\reports\win10_proxy_pipeline_20260309_161239.log`
- `C:\integrator\reports\us_proxy_apply_20260309_161241.log`

## Hardening v2
- Пароль прокси убран из `.env.local`.
- Секрет читается из Windows Credential Manager по `PROXY_CRED_TARGET`.
- Персистентная запись секрета в user env отключена (`USER_ENV_SET=NO`).
- В pipeline реализован backup/restore и явная команда rollback.

## Риски и дыры
1. Direct path может быть недоступен/флапать (exit 28), поэтому direct-check только диагностический.
2. WinHTTP остаётся в direct режиме для SOCKS-контура, системные службы не обязаны идти через прокси.
3. Риск утечки секретов смещён в Credential Manager и локальные backup-файлы.

## Меры снижения риска
- Хранить секрет только в CredMan target `integrator/proxy/us`.
- Не включать `-PersistUserProxyEnv` без необходимости.
- Сохранять backup-папки локально и не выгружать за пределы хоста.
- Проверять логи на отсутствие пароля перед публикацией артефактов.
