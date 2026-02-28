## ✅ agent memory routes: убран hardcode

- Введён единый реестр маршрутов: `agent_memory_routes.py` (`DEFAULT_AGENT_MEMORY_ROUTES`).
- Клиент `agent_memory_client.py` использует `resolve_route(...)` и больше не содержит строкового литерала `/agent/memory/write`.
- Добавлены тесты загрузки/override маршрутов из `gateway.json`.
