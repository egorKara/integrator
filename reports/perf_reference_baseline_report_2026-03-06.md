# Perf reference baseline report (2026-03-06)

## Scope
- Task: P16 — stable perf reference baseline и CI drift-check.
- Goal: закрепить эталон latency baseline как отдельный артефакт и проверять деградацию в CI.

## Reference artifacts
- `reports/perf_baseline_reference.json` — фиксированный baseline для сравнения.
- `reports/perf_baseline_current.json` — текущий baseline, вычисляемый в CI перед check.

## CI contract update
- Workflow шаг `Perf degradation check (baseline contract)` теперь:
  1) пишет current baseline в `reports/perf_baseline_current.json`;
  2) сравнивает `current` против `reference` с порогом `20%`.
- Артефакты CI обновлены: выгружается `reports/perf_baseline_current.json`.

## Verification snapshot
- Local run:
  - `python -m integrator perf baseline --write-report reports/perf_baseline_current.json --json`
  - `python -m integrator perf check --baseline reports/perf_baseline_reference.json --current reports/perf_baseline_current.json --max-degradation-pct 20 --json`
- Result: `status=pass`, деградации выше порога не обнаружено.

## Tests
- Added CI contract test: `tests/test_ci_perf_drift_contract.py`.
- Relevant suite passes after update.
