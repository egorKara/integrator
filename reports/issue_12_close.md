## ✅ Закрыто (контрактные тесты CLI)

- `agents status` (табличный режим): покрыты `--only-problems`, `--explain`, `--fix-hints`, совместно.
- `remotes`: покрыты `--only-github` (skip non-GitHub без nonzero), и кейс пустого origin (строка выводится, exit-code=1).
- `run`: добавлен контракт табличного `--dry-run`, добавлены тесты семантики `--continue-on-error`.
- `localai assistant memory-write`: добавлен тест на отсутствие утечки `--auth-token` в stdout/stderr.
- `default_roots`: добавлены тесты разбора `INTEGRATOR_ROOTS/TAST_ROOTS` (`;`, trimming, пустые сегменты, приоритет env над registry).

### Проверки
- `python -m unittest discover -s tests -p "test*.py"` (169 tests, OK)
- `python -m ruff check .`
- `python -m mypy .`

### Изменённые файлы
- cli_cmd_git.py
- tests/test_projects.py
- tests/test_localai_cli.py
- tests/test_registry.py
