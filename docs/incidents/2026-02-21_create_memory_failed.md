# Incident: Create memory failed

## Summary
- ID: 2026-02-21_create_memory_failed
- Date: 2026-02-21
- Severity: p1
- Status: resolved

## Impact
- What broke: agent memory write workflow
- Who/what was affected: operator workflow using memory-write
- Duration: не зафиксировано

## Detection
- Signal: failed memory-write requests
- First observed: 2026-02-21
- How it was detected: operator run

## Root Cause
- Direct cause: попытка выполнить memory-write при недоступном Agent Memory gateway или при несоответствии маршрута ожидаемому `/agent/memory/write`.
- Contributing factors: отсутствовала формализованная preflight-проверка доступности gateway и контрактные тесты для memory-write CLI.

## Timeline
- 2026-02-21: incident observed
- 2026-02-21: fix applied

## Mitigation and Fix
- Mitigation: проверить агентные проекты и доступность gateway, затем повторить memory-write после устранения проблем доступности/конфигурации.
- Permanent fix: добавлен проверяемый операторский workflow (agents status explain/fix-hints) и контрактные тесты, исключающие утечку `--auth-token` в вывод.

## Verification
- Commands:
  - `python -m integrator doctor`
  - `python ops_checklist.py --no-quality --timeout-sec 120 --json`
  - `python -m unittest discover -s tests -p "test*.py"`
  - `python -m integrator agents status --json --only-problems --explain --fix-hints --roots C:\LocalAI --max-depth 4`
- Artifacts (`reports/`): `reports/incident_2026-02-21_create_memory_failed_verification_20260228.md`

## Prevention
- Follow-up tasks: держать ops checklist как обязательный шаг перед публикацией артефактов.
- Tests added: контрактные тесты для `localai assistant memory-write` (отсутствие утечки `--auth-token`).
- Monitoring/alerts: использовать `integrator agents status --only-problems` для оперативной диагностики проблем gateway.

## Rollback
- Rollback command: `git restore --source=HEAD -- docs/incidents/2026-02-21_create_memory_failed.md reports/incident_2026-02-21_create_memory_failed_verification_20260228.md`
- Preconditions: quality gates pass

## References
- External notes: LocalAI/Notes/Инцидент Create memory failed — разбор и фикс
