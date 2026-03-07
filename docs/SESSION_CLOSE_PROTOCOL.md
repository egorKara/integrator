# Протокол закрытия сессии

## Назначение
- Обеспечить предсказуемое закрытие сессии без повторного поиска правил.
- Гарантировать, что самоанализ, актуализация правил и артефакты закрытия выполняются в одном цикле.

## Триггер
- Команда пользователя: `закрыть сессию` (в любой формулировке).
- Стандартный entrypoint: `python -m integrator session close --json`.

## Канон Session Start
- Перед началом работ создать файл заповедника промтов:
  - `python -c "from datetime import datetime; from pathlib import Path; ts=datetime.now().strftime('%Y-%m-%d-%H%M'); p=Path(r'c:\integrator\.trae\memory') / f'Заповедник промтов - {ts}.md'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('# Заповедник промтов\n\n## Задачи\n', encoding='utf-8')"`
- Проверить, что файл создан в `.trae/memory/` с корректным timestamp в имени.

## Обязательная последовательность
1. Проверить актуальные стандарты: `docs/PROJECT_RULES_FULL.md`, `.trae/rules/project_rules.md`, `docs/SELF_ANALYSIS.md`, `docs/RULES_MAP.md`.
2. Выполнить reconciliation правил:
   - найти устаревшие/противоречивые формулировки;
   - обновить канон и индекс документации;
   - зафиксировать, что изменено.
3. Подготовить глубокий самоанализ по формату `T+A=S`:
   - Тезис;
   - Антитезис;
   - Синтез;
   - Уроки (3–7 пунктов);
   - Next atomic step (один).
4. Сохранить пакет закрытия в `reports/`:
   - `session_close_YYYY-MM-DD.md`;
   - `session_close_YYYY-MM-DD.json`.
5. Синхронизировать governance-артефакты:
   - обновить `reports/priority_execution_tracker_*.csv`;
   - обновить `reports/priority_execution_report_*.md` (результат, риск, QC, ссылки).
6. Обновить Core Memory:
   - сохранить/актуализировать правило закрытия сессии;
   - сохранить переносимые уроки.
7. Выполнить финальную верификацию:
   - валидность JSON артефактов;
   - синхронизация tracker/report/session_close;
   - `python -m tools.check_session_close_consistency --reports-dir reports --json`;
   - quality-gates (`unittest`, `ruff`, `mypy`).

## Единый CLI entrypoint
- Команда: `python -m integrator session close --json`.
- Алиас совместимости: `python -m integrator workflow session close --json`.
- Флаги:
  - `--reports-dir` (папка артефактов, default `reports`);
  - `--date YYYY-MM-DD` (фиксировать дату пакета закрытия);
  - `--task-id` (идентификатор записи синхронизации tracker/report);
  - `--skip-quality` (пропуск `unittest/ruff/mypy`);
  - `--dry-run` (без записи файлов, только расчёт payload/шагов).
- Результат: JSON `kind=session_close_run`, `contract_version=1.0` и поля `status`, `steps`, `checks`, `artifacts`, `errors`, `exit_code`.
- Единый валидатор контракта для тестов и CI: `contract_schemas.validate_session_close_run(payload)`.
- CI smoke entrypoint: `python -m tools.ci_contract_smoke --json --md-path reports/ci_contract_smoke.md` (matrix-сценарии: valid, missing-key, steps-shape, status/exit mismatch, contract_version drift, extra-fields; JSON содержит `validator_errors` и `matrix`).

## Минимальные поля session_close JSON
- `kind`, `date`, `owner`, `status`
- `scope` (tracker/report/основные артефакты)
- `thesis`, `antithesis`, `synthesis`
- `lessons`, `next_atomic_step`
- `verification` (json_parse, tracker_report_sync, tests)
- `risks_next`
- `artifacts`

## Критерий завершения
- Артефакты `MD+JSON` сохранены.
- В трекере и execution-report есть синхронная запись о закрытии сессии.
- Проверки завершены со статусом `pass`.
