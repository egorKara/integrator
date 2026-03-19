---
name: "integrator-cli-engineer"
description: "Integrator CLI implementation skill. Invoke for CLI behavior, parser, command contracts, and CLI quality checks. Do not invoke for standalone security audits or LocalAI/VPN/VPS operations."
---

# Integrator CLI Engineer

## Когда вызывать
- Изменяются команды integrator CLI или их параметры.
- Затронуты парсеры CLI и маршрутизация команд.
- Меняются пользовательские контракты вывода (таблицы, JSON, JSONL).
- Нужен целевой прогон quality checks для CLI-изменений.

## Когда не вызывать
- Нужен только security-аудит без изменения CLI.
- Задача относится к RAG/SSOT/MCP контуру LocalAI.
- Задача относится к VPN/VPS подпроектам.
- Нужен только pre-merge вердикт по PR без изменений кода.

## Scope
- Команды CLI integrator: health/projects/batch/agents/localai/chains/registry/git/tools/session.
- Доменные команды: quality/workflow/perf/incidents/algotrading/obsidian.
- Контракты вывода и совместимость JSONL.

## Verification Loop
1) Сформулировать точный scope изменения CLI.
2) Внести правки в код CLI и tests.
3) Прогнать `unittest`, `ruff`, `mypy`.
4) Подтвердить сохранение CLI-контрактов.
