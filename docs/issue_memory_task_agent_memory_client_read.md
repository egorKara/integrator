# Memory Task (T+A=S) — agent_memory_client: добавить read‑методы

Связанный отчёт:
- [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](file:///C:/integrator/docs/AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)

## Тезис (ситуация)
- Сервер памяти уже поддерживает чтение: `GET /agent/memory/search|recent|retrieve`, `GET /agent/memory/stats`, `POST /agent/memory/feedback`.
- Клиент integrator поддерживает только запись (`memory_write`, `memory_write_file`).

## Антитезис (проблема/риски/неизвестное)
- Без read‑методов integrator не может использовать память как источник данных для автоматизаций.
- Нельзя расширять CLI на чтение без надёжного клиента и тестов.

## Синтез (решение/подход)
- Добавить функции:
  - `memory_search(base_url, q, limit=10, kind=None, min_importance=None, include_quarantined=False, include_deleted=False, auth_token=None)`
  - `memory_recent(base_url, limit=10, kind=None, include_quarantined=False, include_deleted=False, auth_token=None)`
  - `memory_retrieve(base_url, q=None, limit=10, kind=None, module=None, min_trust=None, max_age_sec=None, include_quarantined=False, include_deleted=False, auth_token=None)`
  - `memory_stats(base_url, auth_token=None)`
  - `memory_feedback(base_url, id, rating, notes=None, auth_token=None)`
- Добавить unit‑тесты на:
  - корректное формирование URL и query‑params
  - корректный парсинг JSON и обработку HTTPError

## Верификация (Planned)
- `python -m unittest discover -s tests -p "test*.py"`
- Coverage: новые тесты покрывают все добавленные методы

## Next atomic step
Описать точный формат URL и параметров на основе серверного кода rag_server.py и закрепить его в тестах.

