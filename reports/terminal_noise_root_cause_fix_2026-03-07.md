# Terminal noise root-cause fix — 2026-03-07

## Проблема
- В общем выводе `unittest` регулярно появлялись строки:
  - `cwd not found: X:\definitely_missing_dir`
  - `recipe target not found: ...\Smoke-Test.ps1`

## Причина
- Это не runtime-сбой CLI, а утечка ожидаемого `stderr` из негативных unit-тестов.
- Тесты вызывали `_cmd_localai_assistant(...)` без `redirect_stderr`, поэтому ожидаемые error-сообщения попадали в общий лог тест-прогона.

## Исправление (постоянное)
- Обновлены тесты:
  - `tests/test_cli_cmd_localai_module.py::test_assistant_returns_2_when_cwd_missing`
  - `tests/test_cli_cmd_localai_module.py::test_assistant_returns_2_when_target_missing`
- Добавлен перехват `stderr` и явные проверки текста ошибки в тестах.
- CLI-контракты не изменены; изменён только тестовый harness.

## Верификация
- `python -m unittest tests.test_cli_cmd_localai_module -q` → `OK`.
- Полный цикл:
  - `python -m ruff check .` → `0`
  - `python -m mypy .` → `0`
  - `python -m unittest discover -s tests -p "test*.py"` → `0`
- Проверка логов:
  - `has_cwd_not_found=false`
  - `has_recipe_target_not_found=false`

## Рекомендации
- Для всех негативных тестов, ожидающих ошибку в `stderr`, использовать `redirect_stderr(...)`.
- Проверять отсутствие шумовых строк в агрегированном `unittest` логе как отдельный gate.
