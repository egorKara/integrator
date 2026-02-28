# Memory Task (T+A=S) — Obsidian CLI: внедрение в integrator/LocalAI (EPIC)

Связанные материалы:
- Фиксация фактов и применимость: [OBSIDIAN_CLI_ADOPTION_2026-02-28.md](file:///C:/integrator/docs/OBSIDIAN_CLI_ADOPTION_2026-02-28.md)
- Источник релиза: https://obsidian.md/changelog/2026-02-27-desktop-v1.12.4/
- Документация CLI: https://help.obsidian.md/cli

## Тезис (ситуация)
- Obsidian добавил официальный CLI (`obsidian`) для управления приложением и vault.
- Нам нужен управляемый и безопасный слой интеграции CLI → integrator/LocalAI, чтобы использовать Obsidian как часть пайплайнов (поиск/метрики/диагностика) без неявных write-операций.

## Антитезис (проблема/риски/неизвестное)
- В репозитории отсутствуют команды `integrator obsidian ...`, нет контракта безопасного вызова `obsidian`.
- CLI Obsidian может зависеть от запущенного приложения; тестируемость без реального GUI требует изоляции/моков.
- Команды `obsidian eval` несут риск произвольного выполнения кода внутри приложения; нужен allowlist.
- Новая политика удаления вложений в UI не решает задачу orphan attachments в нашем vault; требуется отдельный отчёт и явная write-команда.

## Синтез (решение/подход)
- Добавить набор read-only команд в `integrator`, которые:
  - диагностируют доступность `obsidian`
  - проксируют поиск/метрики в стабильный JSONL
  - не выполняют write-операции без явного `--apply`
- Добавить набор unit-тестов с подменяемым “бинарником” `obsidian` для детерминированных прогонов.
- Зафиксировать минимальные операционные требования в документации/SSOT.

## Контекст
- Репо/модуль: `egorKara/integrator`
- Цель: интегрировать Obsidian CLI в наши потоки без нарушений принципа “по умолчанию read-only”.

## Список задач (атомарно)
- [ ] Добавить `integrator obsidian doctor` (read-only) и тесты.
- [ ] Добавить `integrator obsidian search` и `integrator obsidian tags` (read-only) и тесты.
- [ ] Добавить отчёт `integrator obsidian attachments report` (read-only) и write-команду с `--apply`.
- [ ] Ограничить `obsidian eval` allowlist и сделать команду выключенной по умолчанию.
- [ ] Зафиксировать в документации/SSOT требования и инструкции включения Obsidian CLI.

## Верификация (Planned)
- `python -m unittest discover -s tests -p "test*.py"`
- `python -m ruff check .`
- `python -m mypy .`
- `python -m integrator --help` и `python -m integrator obsidian --help` (контракт CLI)

## Next atomic step
Создать отдельные issues по каждому пункту списка задач и привязать их к этому EPIC.

