## ✅ EPIC: Agent Memory read API + CLI + task semantics

Выполнено:
- Клиент: добавлены read-методы и вынесены маршруты в реестр (issues #20, #21).
- CLI: добавлены команды чтения memory (issue #22).
- Семантика задач (kind=task) и CLI команды задач (issue #23).

### Верификация
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest discover -s tests -p "test*.py"` (OK)
