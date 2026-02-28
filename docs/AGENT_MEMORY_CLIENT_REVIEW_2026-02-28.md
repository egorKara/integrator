# Отчёт: agent_memory_client — факт‑чек и план внедрения (T+A=S)

Дата фиксации: 2026-02-28

## Источники и объекты анализа
- Клиент: [agent_memory_client.py](file:///C:/integrator/agent_memory_client.py)
- Использование в CLI:
  - [cli_workflow.py](file:///C:/integrator/cli_workflow.py)
  - [cli_cmd_localai.py](file:///C:/integrator/cli_cmd_localai.py)
  - [cli.py](file:///C:/integrator/cli.py)
- Сервер памяти (LocalAI assistant):
  - [rag_server.py](file:///C:/integrator/LocalAI/assistant/rag_server.py)
  - [agent_memory.py](file:///C:/integrator/LocalAI/assistant/app/services/agent_memory.py)
  - [gateway.json](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/config/gateway.json)
  - [memory_write.ps1](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/scripts/memory_write.ps1)
  - [route_task.ps1](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/scripts/route_task.ps1)

## Тезис (что реально уже есть)
### 1) Клиент в integrator — write‑only HTTP JSON с Bearer‑auth
- Реально есть HTTP‑вызов с JSON encode/decode, таймаутом и обработкой HTTPError: [_http_json](file:///C:/integrator/agent_memory_client.py#L36-L68)
- Реально есть запись одной записи памяти: [memory_write](file:///C:/integrator/agent_memory_client.py#L71-L106)
  - Endpoint: `POST /agent/memory/write` (жёстко задан): [agent_memory_client.py:L89](file:///C:/integrator/agent_memory_client.py#L89)
  - Поля payload реально поддерживаются: `summary/content/kind/tags/source/importance/success/metadata/ttl_sec/author/module/trust/confirm_procedure`: [agent_memory_client.py:L90-L105](file:///C:/integrator/agent_memory_client.py#L90-L105)
- Реально есть массовая отправка файла с chunking по символам (chunk_size=20000 по умолчанию): [memory_write_file](file:///C:/integrator/agent_memory_client.py#L109-L143)

### 2) Клиент реально используется в двух местах CLI
- Workflow: `integrator workflow preflight-memory-report` вызывает `memory_write_file`: [_cmd_workflow_preflight_memory_report](file:///C:/integrator/cli_workflow.py#L72-L146)
- LocalAI assistant: `integrator localai assistant memory-write` вызывает `memory_write_file`: [_cmd_localai_assistant](file:///C:/integrator/cli_cmd_localai.py#L23-L73)

### 3) На сервере памяти уже есть чтение/поиск/листинг и локальное хранилище
- Сервер реализует:
  - `POST /agent/memory/write` и `POST /agent/memory/add`: [rag_server.py:L353-L411](file:///C:/integrator/LocalAI/assistant/rag_server.py#L353-L411)
  - `GET /agent/memory/search`, `GET /agent/memory/recent`, `GET /agent/memory/retrieve`, `POST /agent/memory/feedback`, `GET /agent/memory/stats`: [rag_server.py:L413-L504](file:///C:/integrator/LocalAI/assistant/rag_server.py#L413-L504)
- Серверное локальное хранилище реально существует: SQLite + (опционально) FTS5: [AgentMemory._init_db](file:///C:/integrator/LocalAI/assistant/app/services/agent_memory.py#L34-L117)
- В server‑config уже есть реестр routes (в т.ч. для read‑операций): [gateway.json](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/config/gateway.json)

## Антитезис (факт‑чек утверждений из текста; что реально не так/неполно)

### Таблица “утверждение → статус → факт”
| Утверждение из текста | Статус | Факт (подтверждение) |
|---|---:|---|
| “agent_memory_client.py ~144 строки, HTTP клиент write” | Проверено | Файл существует и содержит write‑клиент; объём 143 строки: [agent_memory_client.py](file:///C:/integrator/agent_memory_client.py) |
| “Есть Bearer token / JSON / таймаут” | Проверено | Bearer в заголовке и timeout=10.0: [agent_memory_client.py:L36-L46](file:///C:/integrator/agent_memory_client.py#L36-L46) |
| “Endpoint: POST /agent/memory/write” | Проверено | Жёстко зашит: [agent_memory_client.py:L89](file:///C:/integrator/agent_memory_client.py#L89) |
| “memory_write_file дробит на chunks 20KB” | Противоречиво | По умолчанию 20000, но это символы строки, не байты: [agent_memory_client.py:L115-L132](file:///C:/integrator/agent_memory_client.py#L115-L132) |
| “Нет функций чтения памяти” | Проверено частично | В клиенте нет read/query/list: [agent_memory_client.py](file:///C:/integrator/agent_memory_client.py); на сервере read‑эндпоинты уже есть: [rag_server.py:L413-L504](file:///C:/integrator/LocalAI/assistant/rag_server.py#L413-L504) |
| “Нет локального хранилища” | Проверено частично | В integrator нет, но в сервере есть SQLite store: [agent_memory.py:L34-L117](file:///C:/integrator/LocalAI/assistant/app/services/agent_memory.py#L34-L117) |
| “Нет CLI команд для управления памятью” | Опровергнуто | Есть write‑команды: [cli_workflow.py:L335-L363](file:///C:/integrator/cli_workflow.py#L335-L363), [cli.py:L163-L189](file:///C:/integrator/cli.py#L163-L189) |
| “В cli_workflow.py есть preflight-memory-report и он пишет память” | Проверено | Вызов `memory_write_file`: [cli_workflow.py:L91-L103](file:///C:/integrator/cli_workflow.py#L91-L103) |

### Контрольные вопросы (≥5) с фиксацией факта
1) Где реальный контракт серверных endpoints для чтения? **Проверено:** `search/recent/retrieve/stats/feedback` есть в [rag_server.py](file:///C:/integrator/LocalAI/assistant/rag_server.py#L413-L504).  
2) Есть ли аутентификация на сервере и поддерживает ли её клиент? **Проверено:** сервер проверяет Bearer при `RAG_AUTH_ENABLED=1`: [rag_server.py:L80-L100](file:///C:/integrator/LocalAI/assistant/rag_server.py#L80-L100); клиент выставляет Bearer: [agent_memory_client.py:L43-L46](file:///C:/integrator/agent_memory_client.py#L43-L46).  
3) Есть ли “read‑only” режим и что будет с write‑командами? **Проверено:** write блокируется при `AGENT_WRITE_ENABLED=0` (403): [rag_server.py:L165-L177](file:///C:/integrator/LocalAI/assistant/rag_server.py#L165-L177).  
4) Есть ли единый реестр routes, чтобы убрать hardcode в клиенте? **Проверено:** gateway routes есть: [gateway.json](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/config/gateway.json); в клиенте path захардкожен: [agent_memory_client.py:L89](file:///C:/integrator/agent_memory_client.py#L89).  
5) Есть ли уже “task routing” поверх memory_write? **Проверено:** есть PowerShell‑скрипты `route_task.ps1`/`memory_write.ps1`, которые формируют payload и пишут в memory + metrics: [route_task.ps1](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/scripts/route_task.ps1), [memory_write.ps1](file:///C:/integrator/LocalAI/assistant/projects/agent_gateway/scripts/memory_write.ps1).  
6) Есть ли на сервере “задачи как сущность” (task queue) с фильтрами по статусу? **Не проверено как готовая фича:** в `AgentMemory` есть поиск/листинг, но нет отдельной модели task‑queue; фильтрация по metadata‑полям не реализована: [agent_memory.py](file:///C:/integrator/LocalAI/assistant/app/services/agent_memory.py#L432-L612).  

## Синтез (как реализовать и применить в проекте без переписывания мира)

### Цель внедрения
- Использовать уже существующий сервер памяти как SSOT для “журнала событий” и “поиска по памяти”.
- Добавить в integrator клиентские read‑методы и CLI‑команды чтения, чтобы автоматизации работали без PowerShell‑обвязок.

### План реализации (шаги с проверкой, артефактом и откатом)
1) Зафиксировать контракт endpoints и маршрутов в docs (этот отчёт) и ввести единый реестр routes для integrator‑клиента.  
   - Проверка: grep по `"/agent/memory/write"` возвращает одно место в клиенте.  
   - Артефакт: обновлённый `agent_memory_client.py` без hardcode пути.  
   - Откат: `git restore C:\integrator\agent_memory_client.py`.

2) Добавить read‑методы в `agent_memory_client.py` под существующие серверные endpoints: `memory_search`, `memory_recent`, `memory_retrieve`, `memory_stats`, `memory_feedback`.  
   - Проверка: unit‑тесты на формирование URL/query‑params и парсинг JSON.  
   - Артефакт: новый тестовый модуль `tests/test_agent_memory_client_read.py`.  
   - Откат: `git restore` соответствующих файлов.

3) Добавить CLI команды чтения памяти на базе новых методов клиента.  
   - Проверка: smoke‑прогоны `python -m integrator ... --json` дают стабильный JSONL.  
   - Артефакт: обновлённые `cli.py`/`cli_cmd_localai.py` либо новый `cli_cmd_memory.py`.  
   - Откат: `git restore` изменённых CLI‑модулей.

4) Зафиксировать “задачи для агентов” как минимум в виде формата записи в memory (kind=`task`) и минимального набора CLI команд для создания/закрытия задач через write и поиска pending задач через retrieve/search.  
   - Проверка: демонстрационный сценарий создаёт `kind=task` и достаёт записи по query.  
   - Артефакт: docs‑шаблон task‑записи и smoke‑скрипт в `docs/`.  
   - Откат: `git restore` docs/скриптов.

