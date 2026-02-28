# Obsidian Desktop v1.12.4: Obsidian CLI и применимость к нашим проектам

Дата фиксации: 2026-02-28

## Источники (первичные)
- Changelog Obsidian Desktop v1.12.4: https://obsidian.md/changelog/2026-02-27-desktop-v1.12.4/
- Документация Obsidian CLI: https://help.obsidian.md/cli

## Тезис
- Obsidian добавил официальный CLI (`obsidian`) для скриптинга, автоматизации и интеграции с внешними инструментами.
- Это даёт нам единый “управляемый интерфейс” к vault на уровне приложения, поверх файловой структуры.

## Факты из релиза (проверено)
- Obsidian CLI объявлен как новая функция релиза. Источник: changelog v1.12.4.
- CLI поддерживает разовые команды и интерактивный TUI, умеет `daily`, `search`, `read`, `create`, `tags counts`, `diff`, `eval`. Источник: Obsidian CLI help.
- Таргетинг vault делается через параметр `vault=<name|id>` либо через текущую рабочую директорию. Источник: Obsidian CLI help.
- Добавлен UX-диалог при открытии файлов во внешнем приложении и предупреждение при открытии исполняемых файлов. Источник: changelog v1.12.4.
- Добавлена настройка авто-удаления вложений при удалении заметки (“Always/Ask/Never”). Источник: changelog v1.12.4.

## Что это значит для integrator/LocalAI (проверено по репозиторию)
### 1) Vault уже является сущностью первого класса
- Vault-директория распознаётся сканером проектов как `kind=vault`. Источники: [scan.py](file:///C:/integrator/scan.py#L62-L167), тесты: [test_projects.py](file:///C:/integrator/tests/test_projects.py#L43-L52), [test_projects.py](file:///C:/integrator/tests/test_projects.py#L333-L345).
- Дефолтный `VAULT_ROOT` вычисляется централизованно. Источник: [cli_env.py](file:///C:/integrator/cli_env.py#L37-L47).

### 2) У нас уже есть “обслуживание Obsidian” на уровне файлов
- Есть сценарии нормализации `file:///...` ссылок и абсолютных путей. Источники: [normalize_algotrading_reports_paths.py](file:///C:/integrator/scripts/normalize_algotrading_reports_paths.py), [normalize_algotrading_notes_paths.py](file:///C:/integrator/scripts/normalize_algotrading_notes_paths.py).
- Есть разбор Obsidian image-wikilinks и валидация отсутствующих изображений (доменно для AlgoTrading). Источник: [algo_video_ingest.py](file:///C:/integrator/algo_video_ingest.py#L43-L208).
- В контуре `LocalAI\assistant` уже есть “садовник” и “исполнитель” действий по заметкам (файловые операции, планирование и применение). Источники: [obsidian_gardener.py](file:///C:/integrator/LocalAI/assistant/scripts/obsidian_gardener.py#L1-L327), [obsidian_actions_executor.py](file:///C:/integrator/LocalAI/assistant/scripts/obsidian_actions_executor.py#L18-L128).

## Антитезис (вопросы контроля качества; статус факта)
- Минимальная версия Obsidian Desktop, которая требуется в рабочем процессе: **не зафиксировано** в SSOT/доках текущего репозитория.
- Контракт безопасного вызова `obsidian` из автоматизаций (запрет опасных команд, фиксированный набор allowlist): **не реализовано** в integrator.
- Политика по вложениям (attachments): наличие общих “orphan cleanups” и правил хранения вложений по всему vault: **не реализовано** как общий инструмент (есть доменные проверки на части материалов).

## Синтез (как применяем без ветвлений)
### A) Интеграции уровня integrator (CLI)
1) Реализовано в integrator: `integrator obsidian doctor` (read-only) для диагностики:
   - наличие `obsidian` в PATH/доступность запуска
   - версия Obsidian
   - таргетный `vault_root` и базовые маркеры (`.obsidian/`)
   - JSONL/табличный вывод по контракту integrator
2) Реализовано в integrator: `integrator obsidian search` (read-only) как “мост”:
   - проксирование `obsidian search ...` с жёсткой нормализацией вывода в JSONL
3) Реализовано в integrator: `integrator obsidian tags counts` (read-only) для метрик таксономии:
   - `obsidian tags counts` и сохранение отчёта в артефакты
4) Реализовано в integrator: `integrator obsidian attachments report` (read-only) и `integrator obsidian attachments delete --apply` (write) для orphan attachments.
5) Реализовано в integrator: `integrator obsidian eval` (disabled by default) с `--enable-eval` и allowlist профилей.

### B) Интеграции уровня LocalAI assistant (RAG/индексация)
1) Использовать `obsidian search` как управляемый retrieval-слой поверх активного vault:
   - быстрые выборки по ключам перед формированием контекста
2) Добавить health-check “структуры vault” через `obsidian eval`:
   - строго ограничить allowlist выражений (запрет произвольного JS)

### C) Гигиена вложений (attachments)
1) Ввести отдельный read-only отчёт “orphan attachments candidates”:
   - кандидаты на удаление считаются вне Obsidian (по ссылкам в markdown и фактическим файлам)
   - удаление выполняется только отдельной write-командой с явным `--apply`
