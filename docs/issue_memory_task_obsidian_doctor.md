# Memory Task (T+A=S) — integrator obsidian doctor (read-only)

Связанные материалы:
- [OBSIDIAN_CLI_ADOPTION_2026-02-28.md](file:///C:/integrator/docs/OBSIDIAN_CLI_ADOPTION_2026-02-28.md)
- Obsidian CLI help: https://help.obsidian.md/cli

## Тезис (ситуация)
- Нужна диагностическая команда `integrator obsidian doctor`, чтобы быстро понять готовность окружения к работе с Obsidian CLI.

## Антитезис (проблема/риски/неизвестное)
- `obsidian` может быть не установлен/не зарегистрирован/недоступен в PATH.
- На Windows установка CLI требует действий в самом Obsidian и отдельного шага (описано в help).
- У нас нет стандартизированного вывода “готово/не готово” под JSONL и табличный формат.

## Синтез (решение/подход)
- Реализовать команду `integrator obsidian doctor` (read-only) со стабильными полями:
  - `obsidian_cli_present` (bool)
  - `obsidian_version` (string|null)
  - `vault_root` (string)
  - `vault_markers` (list)
  - `status` (`ok|missing|error`)
- Добавить флаг `--json` и придерживаться контракта JSONL (одна запись — один объект).
- Добавить unit-тесты на:
  - отсутствие `obsidian` (ожидаемо `status=missing`)
  - подменённый “obsidian” (ожидаемо корректное распознавание версии)

## Верификация (Planned)
- `python -m unittest discover -s tests -p "test*.py"`
- `python -m ruff check .`
- `python -m mypy .`
- Smoke: `python -m integrator obsidian doctor` (таблица) и `python -m integrator obsidian doctor --json` (JSONL)

## Next atomic step
Добавить новый CLI-модуль команд `cli_cmd_obsidian.py` и подключить его в `cli.py`.

