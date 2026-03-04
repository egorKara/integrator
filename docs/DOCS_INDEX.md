# Документация (индекс)

## Назначение
- Зафиксировать долговременную истину (SSOT) и рабочие протоколы, чтобы решения не жили только в чате.
- Дать быстрый вход в правила, артефакты и “оперативную память” (Заповедник промптов).

## Навигация
- Правила проекта (полная спецификация): [PROJECT_RULES_FULL.md](./PROJECT_RULES_FULL.md)
- Сводка и приоритет правил (что важнее, когда конфликт): [RULES_MAP.md](./RULES_MAP.md)
- Заповедник промптов (канон + примеры + как пополнять): [ZAPOVEDNIK_PROMPTOV.md](./ZAPOVEDNIK_PROMPTOV.md)
- Самоанализ (шаблон и последний отчёт): [SELF_ANALYSIS.md](./SELF_ANALYSIS.md)
- Obsidian CLI и применимость к нашим проектам: [OBSIDIAN_CLI_ADOPTION_2026-02-28.md](./OBSIDIAN_CLI_ADOPTION_2026-02-28.md)
- Obsidian CLI: EPIC и атомарные задачи (issue bodies): [issue_memory_task_obsidian_cli_epic.md](./issue_memory_task_obsidian_cli_epic.md)
- Agent Memory: задачи (kind=task): [agent_memory_tasks.md](./agent_memory_tasks.md)
- Agent memory client: факт-чек и план внедрения: [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](./AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)
- Agent memory: EPIC и атомарные задачи (issue bodies): [issue_memory_task_agent_memory_epic.md](./issue_memory_task_agent_memory_epic.md)
- GitHub API auth для приватных репозиториев: [GITHUB_API_AUTH.md](./GITHUB_API_AUTH.md)
- GitHub Issues/Projects как внешняя память агента: [GITHUB_ISSUES_PROJECTS_MEMORY.md](./GITHUB_ISSUES_PROJECTS_MEMORY.md)
- GitHub-канон (issues/projects/workflow): [PROJECT_CANON.md](../.github/PROJECT_CANON.md)
- Протокол intake: агент разбирает задачу из GitHub Issue: [AGENT_TASK_INTAKE.md](./AGENT_TASK_INTAKE.md)
- Архитектура и контуры модулей: [ARCHITECTURE.md](./ARCHITECTURE.md)
- LLM Sidecar для анализа артефактов: [LLM_SIDECAR.md](./LLM_SIDECAR.md)
- Журнал и шаблон инцидентов: [INCIDENTS.md](./INCIDENTS.md), [INCIDENT_TEMPLATE.md](./INCIDENT_TEMPLATE.md)
- Политика code review: [CODE_REVIEW.md](./CODE_REVIEW.md)
- Технический changelog: [TECHNICAL_CHANGELOG_2026-02-20.md](./TECHNICAL_CHANGELOG_2026-02-20.md)
- SLI/SLO и эксплуатационные метрики: [SLI_SLO.md](./SLI_SLO.md)

## Принципы оформления (обязательные)
- Любое утверждение “работает” подтверждается артефактами (команда/тест/лог/скрин), либо явно помечается как гипотеза.
- Секреты/токены/пароли никогда не попадают в документы. Допускается только факт “present/len”.
- Формат описания изменений: Тезис → Антитезис → Синтез + Next atomic step (один).
