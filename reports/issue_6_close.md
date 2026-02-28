## ✅ Сделано

- Добавлен скан секрет-паттернов по `git ls-files` (включая `docs/` и другие отслеживаемые файлы).
- Добавлен скан секрет-паттернов по `reports/` (текстовые расширения, лимит размера файла).
- Операторский `ops_checklist.py` теперь запускает guardrails с `--scan-tracked --scan-reports`.

### Проверки
- `python ops_checklist.py --no-quality --timeout-sec 120 --json` (ok=true)
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest discover -s tests -p "test*.py"` (159 tests, OK)

### Изменённые файлы
- guardrails.py
- ops_checklist.py
- tests/test_guardrails.py
