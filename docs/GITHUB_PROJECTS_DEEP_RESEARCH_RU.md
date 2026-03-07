# GitHub Projects: глубокое исследование и применение в Integrator

## Тезис
- GitHub Projects — это не просто доска, а слой управления потоком работы поверх Issues/PR с двусторонней синхронизацией.
- Projects поддерживает таблицу, доску и timeline-представления, пользовательские поля, автоматизации, аналитику и шаблоны.
- Для Integrator это естественная control plane-модель для цикла `Telegram → Issue → Queue → Execution → Report`.

## Ключевые возможности Projects
- **Views:** table/board/timeline с фильтрацией, сортировкой, группировкой, срезами.
- **Поля:** встроенные + пользовательские (date/number/single-select/text/iteration), до 50 полей на проект.
- **Автоматизация:** встроенные workflow-правила (авто-добавление, авто-архивирование, автозаполнение полей).
- **Расширенная автоматизация:** GraphQL API + GitHub Actions для сложной оркестрации.
- **Insights:** диаграммы и аналитика по элементам проекта с кастомными фильтрами.
- **Status updates:** публикация состояния проекта (`On track`, `At risk` и т.д.) с Markdown-сводкой.
- **Templates:** повторно используемые шаблоны проектов для стабильных процессов команды.
- **Двусторонняя синхронизация:** изменения в issue/PR отражаются в Project и наоборот.

## Ограничения и риски
- Projects не «выполняет код» сам по себе; это оркестрация и наблюдаемость, не runtime.
- Без явной state-machine процесс деградирует в «доску без дисциплины».
- Без dedup/idempotency можно дублировать постановки задач в очередь.
- Без SLA/ownership поля `Status` теряют ценность и становятся формальностью.

## Синтез: целевая модель Integrator

### 1) State-machine для задач
- `new` → `queued` → `in_progress` → `blocked` → `done`.
- Источник истины выполнения: issue labels + project Status field.

### 2) Рекомендуемые поля Project
- `Status` (single-select): `Queued`, `In Progress`, `Blocked`, `Done`.
- `Priority` (single-select): `P0/P1/P2`.
- `Source` (single-select): `telegram`, `manual`, `automation`.
- `QueueTS` (date): время постановки в очередь.
- `StartedTS` (date): время начала исполнения.
- `SLI` (number/text): метрика качества (tests pass, lint, etc.).

### 3) Автоматизации
- Авто-добавление в Project при labels `remote,telegram`.
- Авто-архивирование для `done + closed`.
- Правила на обновление `Status` при смене labels (`agent:queued`, `agent:in_progress`, `agent:done`).

### 4) Метрики управления
- Lead Time: `QueueTS → Done`.
- WIP: число `In Progress`.
- Throughput: завершённые задачи за период.
- Blocked Aging: сколько задач в `Blocked` старше порога.

## Что уже применено в репозитории
- Регулярный сканер GitHub задач из Telegram: `tools/telegram_github_worker.py`.
- Автопостановка в локальную очередь: `reports/telegram_github_worker_queue.jsonl`.
- Claim-метка и комментарий в issue: `agent:queued` + служебный комментарий.
- Постоянный автозапуск воркера через Windows Scheduled Task.

## Что добавить следующим шагом
- Интеграция с Project (GraphQL): авто-добавление элемента и выставление `Status=Queued`.
- Исполнитель очереди (agent-run loop): перевод `queued → in_progress → done` с отчётом в issue.
- Единый weekly insights-отчёт (CSV/MD) с метриками lead time/WIP/throughput.
