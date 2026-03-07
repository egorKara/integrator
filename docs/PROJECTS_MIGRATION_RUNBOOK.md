# Runbook: переход из issue-only в GitHub Projects

## Цель
- Вовремя перевести поток задач в GitHub Projects, не усложняя процесс раньше времени.

## Сигнал готовности
- Запуск оценки:
  - `python -m integrator quality projects-migration-readiness --repo egorKara/integrator --json`
- Базовое правило:
  - если `recommend_projects_migration=true`, начинаем миграцию в Projects.

## Шаги миграции
1) Создать board со статусами: `Backlog`, `Ready`, `In Progress`, `Review`, `Done`.
2) Перенести все открытые issue в board.
3) Для каждой issue выставить triage labels (`priority:*`, `type:*`, `status:*`).
4) Настроить SLA на stale issues и еженедельный health-check board.

## Пост-миграционный контроль
- Еженедельно запускать readiness-команду и фиксировать артефакт в `reports/`.
- Следить за метриками:
  - `stale_issues`,
  - `triage_coverage`,
  - доля задач без движения > 7 дней.

## Безопасный откат
- Если board усложняет поток при малом объёме задач:
  - вернуть issue-only режим,
  - оставить только labels + weekly triage.
