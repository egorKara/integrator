# Windows 10 Pro Security Posture — 2026-03-09

## Источник baseline
- `C:\integrator\reports\win10_security_baseline_20260309_161603.md`
- `C:\integrator\reports\proxy_status_snapshot_20260309_100443.log`

## Состояние
- Прокси-контур работает через SOCKS5 с US egress.
- User proxy env очищается pipeline перед применением, секрет не персистится.
- WinHTTP в direct режиме при SOCKS-конфигурации.
- Backup/rollback механизм внедрён и проверяем.

## Риски (приоритет)
1. **Средний:** WinHTTP direct для системных компонентов, возможен обход прокси-контуром отдельных сервисов.
2. **Средний:** Локальные backup-файлы содержат чувствительную конфигурацию (без пароля, но с сетевым контекстом).
3. **Низкий:** Direct-check timeout, влияет на диагностику, не на рабочий proxy egress.

## Что уже закрыто
- Секреты не в `.env.local` для прокси-пароля.
- Пароль не пишется в отчёты pipeline/apply.
- Добавлен явный rollback командой `restore_win10_inet_access.ps1`.

## Следующие меры без смены паролей
1. Поднять pipeline в Scheduled Task с отдельным сервисным контекстом.
2. Ограничить ACL на `C:\integrator\reports\proxy_backup_*`.
3. Добавить регулярный secret-hygiene scan по `reports/*.log` и `*.md`.
