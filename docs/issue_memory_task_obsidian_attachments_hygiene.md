# Memory Task (T+A=S) — отчёт и гигиена вложений (attachments)

Связанные материалы:
- [OBSIDIAN_CLI_ADOPTION_2026-02-28.md](file:///C:/integrator/docs/OBSIDIAN_CLI_ADOPTION_2026-02-28.md)
- Changelog v1.12.4 (attachment cleanup UI): https://obsidian.md/changelog/2026-02-27-desktop-v1.12.4/

## Тезис (ситуация)
- В Obsidian появился UX для удаления вложений вместе с заметкой.
- Нам нужен инструмент, который находит orphan attachments в нашем vault и управляет их удалением по контракту “по умолчанию read-only”.

## Антитезис (проблема/риски/неизвестное)
- UI-настройка Obsidian не покрывает массовые “сироты” от исторических правок, импортов и переименований.
- Удаление вложений без бэкапа ломает воспроизводимость отчётов и артефактов.

## Синтез (решение/подход)
- Добавить команды:
  - `integrator obsidian attachments report` (read-only): строит список кандидатов orphan attachments
  - `integrator obsidian attachments delete --apply` (write): удаляет только то, что в отчёте, с обязательным бэкапом
- Политика:
  - по умолчанию ничего не удалять
  - перед удалением создавать бэкап каталога вложений (в заданный `--backup-dir`)
  - на каждом шаге сохранять отчёт в `reports/`

## Верификация (Planned)
- Unit-тесты на временном vault:
  - заметка со ссылкой на attachment (не кандидат)
  - файл-вложение без ссылок (кандидат)
- Smoke: `python -m integrator obsidian attachments report --json`

## Next atomic step
Зафиксировать формальное определение “orphan attachment” для markdown/wikilinks.

