# Memory Task (T+A=S) — integrator obsidian search + tags (read-only)

Связанные материалы:
- [OBSIDIAN_CLI_ADOPTION_2026-02-28.md](file:///C:/integrator/docs/OBSIDIAN_CLI_ADOPTION_2026-02-28.md)
- Obsidian CLI help: https://help.obsidian.md/cli

## Тезис (ситуация)
- Нужно использовать Obsidian CLI как управляемый слой поиска и метрик по активному vault для пайплайнов LocalAI.

## Антитезис (проблема/риски/неизвестное)
- Вывод `obsidian search` и `obsidian tags counts` не гарантированно удобен для машинного потребления.
- Нужен стабильный JSONL-вывод integrator для последующей агрегации/сохранения отчётов.

## Синтез (решение/подход)
- Добавить команды:
  - `integrator obsidian search --query "..." [--vault <name|id>]`
  - `integrator obsidian tags counts [--vault <name|id>]`
- Реализовать нормализацию вывода в JSONL:
  - поле `kind` (`obsidian_search_result` / `obsidian_tag_count`)
  - поле `vault` (string)
  - поле `payload` (структурированные значения)
- Добавить режим `--copy` не реализовывать на стороне integrator; использовать только внутренние форматы вывода.

## Верификация (Planned)
- Unit-тесты с подменяемым “obsidian” (мок-вывод) и проверкой JSONL.
- Smoke: `python -m integrator obsidian search --query "TODO" --json`
- Smoke: `python -m integrator obsidian tags counts --json`

## Next atomic step
Определить формат JSONL для `search` и `tags` и зафиксировать его в тестах.

