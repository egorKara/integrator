# Issue #33 — Отслеживание момента перехода в GitHub Projects

## Реализация
- Добавлена команда:
  - `python -m integrator quality projects-migration-readiness --repo <owner/repo> --json`
- Команда рассчитывает readiness-score по метрикам:
  - количество open issues,
  - количество open PR,
  - количество stale issues,
  - triage coverage по labels.

## Критерий рекомендации
- Рекомендует переход в Projects, если score >= threshold (по умолчанию `2`).
- Выдаёт причины и next actions для запуска board/автоматизаций.

## Артефакт актуальной оценки
- `reports/projects_migration_readiness_20260307_issues33.json`
- Текущий результат: `recommend_projects_migration=true`.

## Операционный цикл
1) Запускать оценку ежедневно или при росте входящего потока задач.
2) При `recommend_projects_migration=true` — запускать board migration runbook.
3) После миграции — мониторить stale issues и triage coverage как контрольные KPI.
