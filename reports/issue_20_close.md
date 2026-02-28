## ✅ agent_memory_client: добавлены read-методы

- Добавлены методы чтения: `memory_search`, `memory_recent`, `memory_retrieve`, `memory_stats`, `memory_feedback`.
- Добавлены unit-тесты на URL/query-params, payload feedback и переопределение маршрута.

### Проверки
- `python -m unittest tests.test_agent_memory_client` (OK)
- `python -m ruff check .`
- `python -m mypy .`
