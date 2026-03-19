---
name: "localai-assistant-ops"
description: "LocalAI assistant operations orchestration skill. Invoke for RAG/SSOT/indexing/MCP runtime operations and cross-module diagnostics. Do not invoke for narrow architecture/code/performance/test-only tasks."
---

# LocalAI Assistant Ops

## Когда вызывать
- Нужна эксплуатация RAG Proxy, MCP, indexer и health-контуров.
- Нужна сквозная диагностика LocalAI assistant между несколькими модулями.
- Требуется проверка SSOT-конфига и согласованности runtime-путей.

## Когда не вызывать
- Нужен чисто архитектурный совет без runtime-операций.
- Нужен локальный анализ кода, только метрики или только тест-план.
- Нужна базовая security-проверка без LocalAI runtime-контекста.

## Scope
- LocalAI assistant сервисы (RAG Proxy, MCP, Indexer).
- SSOT: Контроль конфигурации и путей через `${VAULT_ROOT}\LocalAI\10-Config.md`.
- Индексация: Vector DB, chunking, re-ranking.

## Источники истины (T+A=S)
- **SSOT Config:** `${VAULT_ROOT}\LocalAI\10-Config.md` (дефолт `C:\vault\Projects`).
- **Env:** `.env` в корне репозитория.
- **Code:** `${LOCALAI_ROOT}\assistant` (дефолт `C:\LocalAI\assistant`).

## Нормальный рабочий цикл
1) **Status:** Проверить доступность сервисов (`integrator localai assistant rag --daemon`).
2) **Config:** Проверить переменные окружения (`LOGS_ROOT`, `RAG_BASE_URL`).
3) **Index:** Запустить `index_ssot.py` при изменении данных.
4) **Logs:** Анализировать `rag_server.err` и `mcp_server.log`.

## Типовые задачи
- Диагностика RAG Proxy и MCP (проверка портов 8000/8011).
- Оптимизация параметров (Context Window, K, Chunk Size).
- Обслуживание индексов (reindex, cleanup).

## Примеры команд
- Запуск RAG: `python -m integrator localai assistant rag --cwd C:\LocalAI\assistant --daemon`
- Индексация: `python C:\LocalAI\assistant\index_ssot.py`
- Валидация: `python C:\LocalAI\assistant\scripts\validate_ssot.py`
