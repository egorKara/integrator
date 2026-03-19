# P17 Phase-1 rollback runbook

## Trigger criteria
- `p17_phase1_gate` возвращает `status=fail`.
- `perf_degraded_count > 0` при пороге `20%`.
- Потеря event ingestion (`events_processed_rate < 0.95`) или нулевая issue-эмиссия.

## Rollback actions
1. Отключить phase-1 gate в CI для аварийного восстановления пропускной способности.
2. Вернуть предыдущий стабильный `reports/perf_baseline_reference.json`.
3. Откатить изменения P17 в workflow и checker до последнего зелёного состояния.
4. Перезапустить worker/executor и подтвердить восстановление event-потока.

## Verification after rollback
- `python -m integrator perf check --baseline reports/perf_baseline_reference.json --current reports/perf_baseline_current.json --max-degradation-pct 20 --json`
- `python -m tools.check_p17_phase1_gate --reports-dir reports --docs-dir docs --json`
- Проверка CI job `test` в GitHub Actions: status `success`.
