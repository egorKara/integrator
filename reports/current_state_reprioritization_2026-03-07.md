# Current State + Reprioritization (2026-03-07)

## Текущее положение
- Preflight контур стабилен: `doctor`, `projects list`, `agents list/status` проходят.
- Quality-контур стабилен: `ruff`, `mypy`, `unittest` проходят на актуальном состоянии.
- Governance-контур обновлён:
  - есть `quality projects-migration-readiness`,
  - есть `quality mcp-tools-inventory`,
  - есть runbook миграции в GitHub Projects,
  - добавлен мини-словарь терминов как база знаний.
- Repo readiness по branch protection остаётся с внешним ограничением API shape (`shape_unsupported`) для required status checks payload.
- GitHub backlog закрыт: `open_issues=0`.

## Что выполнено в этом цикле
- Добавлен мини-словарь: `docs/INTEGRATOR_MINI_GLOSSARY.md`.
- Добавлен runbook: `docs/PROJECTS_MIGRATION_RUNBOOK.md`.
- Обновлены индексы/quickstart:
  - `docs/DOCS_INDEX.md`
  - `OPERATIONS_QUICKSTART.md`
- Адаптированы skills/agents без потери функционала:
  - `.trae/skills/integrator-cli-engineer/SKILL.md`
  - `.trae/skills/security-ops/SKILL.md`
  - `.trae/skills/claude-stealth-connect-ops/SKILL.md`
  - `.trae/skills/vpn-manager-maintainer/SKILL.md`
  - `AGENTS.md`
- Интегрирован MCP tools inventory:
  - `cli_quality.py` (`quality mcp-tools-inventory`)
  - `tests/test_cli_quality_module.py` (coverage команды)
  - `reports/issue_35_mcp_tools_research_integration_2026-03-07.md`

## Новая расстановка приоритетов
- P0: Поддерживать нулевой backlog по open issues и SLA реакции на новые задачи.
- P1: Удерживать issue-only поток, пока `projects-migration-readiness` не подаст устойчивый сигнал на миграцию.
- P1: Довести triage coverage до >= 0.6 для устойчивой приоритизации.
- P1: Использовать `mcp-tools-inventory` как еженедельный инвентарь MCP-серверов.
- P2: Продолжить research-направления (монетизация/Telethon/vibe-coding) через пилоты и метрики.

## Принятое решение
- По текущим метрикам не форсировать миграцию в Projects board.
- Работать в issue-only режиме с регулярным запуском readiness-команды и weekly triage.
