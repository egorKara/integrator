# Pattern refactor cycle — 2026-03-07

## Scope
- Область: повторяющиеся паттерны захвата stdout/stderr в CLI-негативных тестах.
- Цель: стандартизовать, сократить дублирование, исключить шум в unittest-логах, добавить регулярный автоматический контроль.

## Применённый шаблон
- Вынесен единый helper: `tests/io_capture.py`:
  - `capture_stdio()`
  - `capture_stderr_call(...)`
- Рефакторинг сделан в:
  - `tests/test_cli_cmd_localai_module.py`
  - `tests/test_projects.py`
  - `tests/test_obsidian_cli.py`
  - `tests/test_session_close_workflow.py`
  - `tests/test_ci_contract_smoke.py`
  - `tests/test_perf_baseline.py`

## Антидубль и регулярность
- Добавлен кроссплатформенный noise gate: `python -m tools.check_negative_tests_stderr --log-path reports/unittest.log --json`.
- Gate встроен в Linux и Windows CI jobs в `.github/workflows/ci.yml`.
- Операционный runbook обновлён: `OPERATIONS_QUICKSTART.md`.

## Практики из внешних источников
- Подтверждён продуктивный паттерн `redirect_stdout/redirect_stderr` с единым context-manager helper для тестов и проверок буферов.
- Для логгера — отдельный паттерн `assertLogs()` вместо перехвата stdout/stderr.

## Источники
- https://adamj.eu/tech/2025/08/29/python-unittest-capture-stdout-stderr/
- https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html
