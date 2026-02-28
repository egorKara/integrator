# Memory Task (T+A=S) — семантика “task” поверх agent memory

Связанный отчёт:
- [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](file:///C:/integrator/docs/AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)

## Тезис (ситуация)
- Есть серверное хранилище памяти и поиск по нему.
- Есть write‑поток событий (event) через integrator и agent_gateway.

## Антитезис (проблема/риски/неизвестное)
- Нет единого контракта, как представлять задачу агента в памяти.
- Нет команд `task-add/tasks-pending/task-close` в integrator.
- На сервере нет фильтра по metadata‑полям; поиск работает по summary/content.

## Синтез (решение/подход)
- Зафиксировать формат записи задачи:
  - `kind="task"`
  - `summary="[TASK] <title>"`
  - `content` содержит структуру полей в markdown (Status/Priority/Owner/Next step)
  - `tags` содержит `task`, `status:open|done`, `prio:p0|p1|p2`
- Реализовать CLI команды:
  - `task-add` (создаёт запись kind=task)
  - `tasks-pending` (retrieve/search по `tags=status:open` и `query="[TASK]"`)
  - `task-close` (пишет follow-up запись kind=event с ссылкой на task id и tag `status:done`)
- Запретить автоматическое изменение существующих task записей, использовать только append‑модель.

## Верификация (Planned)
- Smoke: создать task, затем найти его в `tasks-pending`.
- Smoke: закрыть task, затем `tasks-pending` его не возвращает при запросе `status:open`.

## Next atomic step
Определить точный шаблон markdown для task content и закрепить в тестах как snapshot.

