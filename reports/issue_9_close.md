## ✅ Исправлено

- Исправлено вычисление repo root для чтения `.trae/global_gitignore_localai` (раньше уходило в `C:\`).
- `git bootstrap-ignore` теперь тестируется без mock и реально читает `.trae/global_gitignore_localai`.
- Для `status/remotes/report` при `--json` добавлено поле `error` при `WorkerError`.

### Проверки
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest discover -s tests -p "test*.py"` (157 tests, OK)

### Изменённые файлы
- utils.py
- cli_cmd_git.py
- tests/test_utils.py
- tests/test_projects.py
