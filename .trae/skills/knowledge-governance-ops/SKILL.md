---
name: "knowledge-governance-ops"
description: "Governs Agent Memory, Obsidian, and GitHub memory-loop workflows. Invoke for KB intake, traceability, and knowledge consistency checks. Do not invoke for low-level feature coding."
---

# Knowledge Governance Ops

## Когда вызывать

- Нужно вести цикл знаний Agent Memory + Obsidian + GitHub Issues.
- Нужна трассируемость задачи: источник, решение, артефакты, статус.
- Нужно проверить согласованность SSOT/KB/операционных заметок.
- Нужно сформировать intake-пакет задач для базы знаний.

## Когда не вызывать

- Нужен низкоуровневый refactor кода CLI или модулей.
- Нужен узкий CVE triage без контекста базы знаний.
- Нужны VPS/VPN операционные действия.

## Scope

- Контур знаний: Agent Memory, Obsidian, GitHub memory-loop.
- Governance-артефакты: индекс, intake, traceability, lifecycle статусы.
- Проверка полноты связей между docs/reports/issues.

## Рабочий цикл

1) Собрать входы: issue/notes/memory/tasks.
2) Нормализовать статусы и связи артефактов.
3) Проверить traceability и отсутствие конфликтов.
4) Сформировать итоговый governance-отчёт и рекомендации.

## Security Gate

- Перед merge применять `github-security-reviewer`.
