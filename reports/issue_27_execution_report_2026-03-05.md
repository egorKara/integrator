# Issue #27 execution report (2026-03-05)

## Scope
- Issue: `#27`
- Запрос: найти файл с перечнем незавершённых задач, зафиксировать факт, проанализировать важность, начать выполнение.

## Фактическое состояние (проверено)
- Основной перечень незавершённых top-приоритетов: `reports/project_top6_priorities_2026-03-04.json`.
- Незавершённые пункты: `P16`, `P17` (после закрытия `P13`, `P14`, `P15`).
- Отчёт исполнения подтверждает, что следующий этап — `P13–P17`: `reports/priority_execution_report_2026-03-04.md`.
- Follow-up план содержит открытые позиции со статусами `In progress`/`Planned`: `reports/recommendations_followup_plan_2026-02-20.md`.
- Обнаружен дрейф между backlog и tracker по части статуса исторических блоков.

## Приоритизация
- **Критический контур:** `P13` (JSON/JSON-strict контракт batch-run).
- **Высокий:** `P14` (execution-plan consistency checker).
- **Средний:** `P15` (profile calibration), `P16` (perf baseline), `P17` (EPIC kickoff).

## Исполнение, запущенное сейчас
- Включён регулярный GitHub-воркер сканирования задач из Telegram.
- Для issue установлен признак постановки в execution flow (`agent:queued` + комментарий).
- Подготовлен следующий шаг: перевод в `agent:in_progress` и выполнение `P13` как первого блока.

## Выполнено по P13
- Добавлены негативные контрактные сценарии `run --json --json-strict`:
  - `quiet-tools` подавляет успешные tool-streams.
  - `continue-on-error` сохраняет валидный JSONL для всех проектов в батче.
  - `tool-missing` (exit 127) не ломает JSONL stdout и корректно уходит в stderr.
  - `strict-roots` abort-path возвращает exit `2`.
- Добавлен golden-тест JSONL-контракта для strict+continue-on-error.
- Прогон тестов: `72 tests OK` по релевантным модулям CLI/worker/executor.

## Выполнено по P14
- Добавлен checker согласованности execution-plan артефактов: `tools/check_execution_plan_consistency.py`.
- Добавлены тесты checker: `tests/test_execution_plan_consistency.py`.
- Добавлены CI шаги `Execution plan consistency` в Linux и Windows workflow.
- Добавлен JSON SSOT для `recommendations_execution_plan_2026-02-20.md` и связка JSON↔MD.
- Верификация checker на реальных артефактах: `status=pass`, проверены 2 пары plan-файлов.

## Выполнено по P15
- Откалиброваны профили `research/coding/ops` в `zapovednik_policy.py` с монотонным разделением чувствительности `ops > coding > research`.
- Добавлены тесты калибровки в `tests/test_zapovednik.py`:
  - порядок чувствительности профилей,
  - `ops` закрывается раньше `coding`,
  - `coding` закрывается раньше `research`.
- Зафиксирован артефакт калибровки: `reports/profile_calibration_report_2026-03-06.md`.
- Верификация: `python -m unittest ...` (85 tests OK по релевантным модулям).

## Выполнено по P16
- Зафиксирован стабильный эталон: `reports/perf_baseline_reference.json`.
- Обновлён CI drift-контур: сравнение `perf_baseline_current.json` против `perf_baseline_reference.json` с порогом `20%`.
- Добавлен контрактный тест CI: `tests/test_ci_perf_drift_contract.py`.
- Зафиксирован артефакт исполнения: `reports/perf_reference_baseline_report_2026-03-06.md`.
- Верификация:
  - `python -m integrator perf check --baseline ...reference... --current ...current... --max-degradation-pct 20 --json` → pass.
  - `python -m unittest ...` по релевантным модулям → pass.

## Выполнено по P17
- Запущен phase-1 kickoff EPIC с machine-checkable gate: `tools/check_p17_phase1_gate.py`.
- Добавлен rollback-контур: `docs/P17_ROLLBACK.md`.
- Добавлен phase-1 kickoff артефакт с SLI snapshot: `reports/p17_phase1_kickoff_report_2026-03-06.md`.
- CI дополнен шагом `P17 phase1 gate` в Linux и Windows workflow.
- Добавлены тесты gate-контракта: `tests/test_p17_phase1_gate.py` и расширен `tests/test_ci_perf_drift_contract.py`.
- Верификация:
  - `python -m tools.check_p17_phase1_gate --reports-dir reports --docs-dir docs --json` → `status=pass`.
  - `python -m unittest ...` по релевантным модулям → pass.

## Next action
- Top-6 backlog (`P12..P17`) закрыт; перейти к исполнению FIFO очереди issue (`#28`).
