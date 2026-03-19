# Terminal noise permanent fix — 2026-03-07

## Что исправлено
- Распространён перехват `stderr` на негативные тесты, где ожидается non-zero код:
  - `tests/test_projects.py`
  - `tests/test_obsidian_cli.py`
  - `tests/test_session_close_workflow.py`
  - `tests/test_session_close_consistency.py`
  - `tests/test_ci_contract_smoke.py`
  - `tests/test_perf_baseline.py`
- Сохранён прежний runtime-поведенческий контракт CLI; изменения только в тестовом harness.

## CI-защита от рецидива
- В `.github/workflows/ci.yml` добавлен `Noise gate (unittest log)` для Linux и Windows.
- Gate валит сборку, если в `reports/unittest.log` найдены строки:
  - `cwd not found:`
  - `recipe target not found:`

## Верификация
- Таргет-прогон изменённых тестов: `OK`.
- Полный цикл качества: `ruff=0`, `mypy=0`, `unittest=0`.
- Проверка агрегированного unittest-лога:
  - `has_cwd_not_found=false`
  - `has_recipe_target_not_found=false`

## Рекомендации
- Для всех новых негативных тестов с ожидаемыми ошибками применять `redirect_stderr(...)`.
- Оставить `Noise gate` обязательным этапом в CI для предотвращения возвращения терминального шума.
