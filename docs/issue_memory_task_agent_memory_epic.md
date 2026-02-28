# Memory Task (T+A=S) — EPIC: Agent Memory (read API + CLI + task semantics)

Связанный отчёт:
- [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](file:///C:/integrator/docs/AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)

## Тезис (ситуация)
- В integrator есть write‑only клиент `agent_memory_client.py` и две CLI‑команды, которые пишут в сервер памяти.
- На сервере памяти уже реализованы read‑эндпоинты (`search/recent/retrieve/stats/feedback`) и SQLite‑хранилище.

## Антитезис (проблема/риски/неизвестное)
- В integrator отсутствуют клиентские методы чтения и отсутствуют CLI‑команды чтения памяти.
- В integrator захардкожен маршрут `"/agent/memory/write"`, хотя существует реестр routes в gateway.json.
- Семантика “задача агента” не формализована как контракт; нет стандарта, как искать pending задачи.

## Синтез (решение/подход)
- Добавить read‑методы в `agent_memory_client.py` под существующие серверные endpoints.
- Убрать hardcode маршрутов и перейти на единый реестр routes.
- Добавить CLI‑команды чтения памяти и минимальную семантику задач (kind=`task`) на базе retrieve/search.

## Дочерние задачи (issues)
- [ ] Добавить read‑методы в agent_memory_client.py и тесты.
- [ ] Вынести маршруты в реестр routes и использовать его в клиенте.
- [ ] Добавить CLI команды чтения памяти (search/recent/retrieve/stats/feedback).
- [ ] Зафиксировать семантику задач (kind=task) и добавить CLI команды задач.

## Верификация (Planned)
- `python -m unittest discover -s tests -p "test*.py"`
- `python -m ruff check .`
- `python -m mypy .`
- Smoke: `python -m integrator ... --json` для каждой новой команды

## Next atomic step
Создать отдельные issues по списку дочерних задач и привязать их к EPIC.

