---
name: "localai-assistant-ops"
description: "Operates LocalAI assistant RAG stack, SSOT, indexing, and diagnostics. Invoke when tasks touch LocalAI assistant services, SSOT, indexing, or RAG troubleshooting."
---

# LocalAI Assistant Ops

## Scope
- LocalAI assistant сервисы, RAG proxy, индексация и контроль SSOT.
- Скрипты обслуживания и диагностики из C:\LocalAI\assistant\scripts.
- Проверка канонических путей и URL через SSOT.

## Источники истины
- SSOT: C:\vault\Projects\LocalAI\10-Config.md
- Project Passport: C:\vault\Projects\LocalAI\Self\project_passport.md

## Нормальный рабочий цикл
1) Проверить SSOT на пути и URL сервисов.
2) Проверить доступность RAG сервера по rag_health_url.
3) Проверить состояние индекса и статус логов в logs_root.
4) При необходимости запустить reindex и обновить метаданные.

## Типовые задачи
- Диагностика RAG Proxy, LM Studio и health endpoint.
- Индексация: запуск index_ssot.py и контроль vector_db.
- Обслуживание Obsidian‑vault: gardener/cleanup/auto tagging.
- Сборка отчётов состояния через существующие скрипты.

## Примеры команд
- Проверка SSOT: `python C:\LocalAI\assistant\scripts\validate_ssot.py`
- Проверка индекса: `python C:\LocalAI\assistant\scripts\index_ssot.py`
- Запуск RAG: `python C:\LocalAI\assistant\rag_server.py`
