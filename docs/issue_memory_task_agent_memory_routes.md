# Memory Task (T+A=S) — убрать hardcode маршрутов agent memory (routes registry)

Связанный отчёт:
- [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](file:///C:/integrator/docs/AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)

## Тезис (ситуация)
- В integrator клиент жёстко использует `"/agent/memory/write"`.
- В LocalAI assistant уже есть реестр маршрутов `gateway.json` с `memory_write/memory_recent/memory_search/...`.

## Антитезис (проблема/риски/неизвестное)
- Hardcode ломает совместимость при изменении путей на сервере.
- Разные источники истины (`gateway.json` и код клиента) увеличивают риск расхождений.

## Синтез (решение/подход)
- Ввести единый источник truth для маршрутов в integrator:
  - модуль `agent_memory_routes.py` с константами путей
  - опциональное чтение `gateway.json` с валидацией схемы
- Перевести `agent_memory_client.py` на использование реестра путей.

## Верификация (Planned)
- Unit‑тест: при изменении пути в реестре клиент использует новый путь.
- Grep‑чек: в репозитории нет строкового литерала `"/agent/memory/write"` вне реестра.

## Next atomic step
Выделить константу пути `MEMORY_WRITE_PATH` и заменить использование строкового литерала в клиенте.

