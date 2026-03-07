# Issue #35 — MCP tools: исследование и интеграция

## Исследование
- MCP tools-подход в контексте проекта нужен для централизованного управления MCP-серверами и прозрачного инвентаря.
- В integrator уже есть запуск MCP (`localai assistant mcp`), но не было отдельного инвентаря “какие MCP-серверы есть и как их поднимать”.

## Интеграция
- Добавлена команда:
  - `python -m integrator quality mcp-tools-inventory --json`
- Что делает:
  - читает `registry.json`,
  - ищет `mcp_server.py` в roots,
  - строит список MCP-серверов и готовые команды запуска.
- Добавлен support `--roots` для внешних директорий.

## Артефакты
- Код: `cli_quality.py` (команда `mcp-tools-inventory`).
- Тесты: `tests/test_cli_quality_module.py` (новые тесты inventory).
- Документация: `OPERATIONS_QUICKSTART.md` (команда добавлена в governance-блок).

## Практическая польза
- Быстрый ответ на вопрос “какие MCP-серверы реально доступны сейчас”.
- Единый JSON-артефакт для автоматизаций и дальнейшего orchestration.
