# Техническая документация изменений (2026-02-20)

## 1. Документация изменений

### 1.1 Изменения кода, архитектуры и конфигураций
- Изменена логика вывода `doctor`: выводится фактический `sys.executable` вместо результата `shutil.which("python")`.
- Добавлены dev-зависимости в `pyproject.toml` через `project.optional-dependencies.dev`.
- Добавлены новые документы и артефакты качества в `reports/`.
- Добавлен файл `.gitignore` для исключения `vault/`, backup-архивов, кэшей и отчетов покрытия.
- Созданы `requirements.txt`, `.env.example` и `tools/dev_setup.ps1` для подготовки новой сессии.
- Выполнен рефакторинг структуры: устранена вложенность `integrator/integrator`, модули перенесены в корень.
- Добавлен CI-конвейер GitHub Actions с gates (ruff/mypy/unittest/coverage ≥ 80%).
- Добавлены шаблон PR и политика code-review.
- Исправлена логика git-операций: статус/remote привязаны к `.git` проекта, без зависимости от родительского репозитория.
- Добавлены целевые unit-тесты для `utils.py`, поднято покрытие `utils.py` до 96%.

### 1.2 Причины решений и альтернативы
- `doctor` -> `sys.executable`: причина — устранение расхождения между выводом `doctor` и фактическим интерпретатором.
  - Альтернативы: оставить `shutil.which("python")` (неустойчиво при WindowsApps alias), или настраиваемый путь через ENV (добавляет конфигурационный долг).
- Dev-зависимости в `pyproject.toml`: причина — декларативность и воспроизводимость окружения.
  - Альтернативы: держать только `requirements.txt` без `pyproject` или использовать `pip-tools`.
- `.gitignore` с `vault/`: причина — предотвращение включения длинных путей и не относящихся к проекту артефактов.
  - Альтернативы: ручное игнорирование при каждом коммите.
- `requirements.txt`: причина — фиксированные версии для быстрой установки без анализа зависимости.
  - Альтернативы: `requirements.lock.txt` или `pip-tools` (требует отдельной сборки).
- Плоская структура модулей: причина — устранение дублирующих путей и упрощение импортов.
  - Альтернативы: оставить `integrator/` как пакет или перейти на `src/` (не соответствовало требованию убрать одинаковые вложенности).

### 1.3 Затронутые файлы, модули, зависимости
- Код:
  - `cli.py` — исправление вывода python path в `doctor`.
- Конфигурации:
  - `pyproject.toml` — добавлены `project.optional-dependencies.dev`.
  - `.gitignore` — исключение `vault/`, кэшей, архивов и `reports/coverage.xml`.
  - `.env.example` — пример переменных окружения.
- Документация и отчеты:
  - `docs/TECHNICAL_CHANGELOG_2026-02-20.md`
  - `reports/quality_report_2026-02-20.md`
  - `reports/coverage.xml`
- Артефакты:
  - `requirements.txt`
  - `tools/dev_setup.ps1`
  - `reports/audit_snapshot_2026-02-20.json`
- Рефакторинг структуры:
  - `integrator.py`, `version.py`, `__main__.py`, `app.py`, `cli.py`, `agents_ops.py`, `run_ops.py`, `scan.py`, `git_ops.py`
  - `chains.json`, `registry.json`

### 1.4 Обратно несовместимые изменения и миграции
- Изменён формат вывода `doctor` для `python` (теперь выводит `sys.executable`).
  - Миграция: если есть парсеры, ожидающие путь WindowsApps, обновить на фактический путь Python.
- Добавлен `.gitignore` с исключением `vault/`.
  - Миграция: если ранее планировалось версионировать `vault/`, его необходимо перенести в отдельный репозиторий.
- Изменены пути импортов: `integrator.*` заменены на прямые модули в корне.
  - Миграция: обновить импорты в собственных скриптах, использовать `from cli import ...`, `from app import ...`.

### 1.5 Рефакторинг структуры каталогов
- Удалена цепочка `integrator/integrator` путём переноса модулей на уровень корня.
- Добавлен `integrator.py` как точка входа для `python -m integrator`.
- `__init__.py` заменён на `version.py` для хранения версии.

## 2. Подготовка к новой сессии

### 2.1 README
Обновлён разделы установки, запуска, тестов, coverage и подготовки окружения.

### 2.2 Конфигурации и .env
Актуализирован пример `.env.example` для параметров RAG и агентных маршрутов.

### 2.3 Инициализация dev-среды
Добавлен `tools/dev_setup.ps1` для создания venv и установки зависимостей.

### 2.4 Зависимости с фиксированными версиями
Добавлен `requirements.txt` с pin-версиями на основе актуального окружения.

### 2.5 Восстановление базы данных и тестовых данных
Используются файлы:
- `C:\LocalAI\cache\agent_memory.db`
- `C:\LocalAI\logs\agent_metrics.jsonl`
- `C:\LocalAI\logs\rag_metrics.jsonl`

Процедура:
1. Восстановить файлы из бэкапа в указанные пути.
2. Проверить доступность `rag_server.py` и запуск в режиме `RAG_PORT=8011`.
3. Запустить `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`.

## 3. Контроль качества

### 3.1 Тесты
- `python -m unittest discover -s tests -p "test*.py"`

### 3.2 Coverage
- `python -m coverage run -m unittest discover -s tests -p "test*.py"`
- `python -m coverage report -m`
- `python -m coverage xml -o reports/coverage.xml`

### 3.3 Известные issues и ограничения
- Coverage общий 86%; низко покрытые модули: `agent_memory_client.py` (23%), `git_ops.py` (63%).
- `Test-NetConnection` может не выводить boolean при отсутствии `-InformationLevel Detailed`, поэтому для проверки порта использован `TcpClient.Connect`.
- `rag_server.py` запускается как dev-сервер Flask, что не подходит для production.

### 3.4 Чек-лист перед новой сессией
1. `python -m integrator doctor`
2. `python -m ruff check .`
3. `python -m mypy . tests`
4. `python -m unittest discover -s tests -p "test*.py"`
5. `python -m coverage report -m`
6. `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`

## 4. Артефакты

### 4.1 Версионирование
- Коммит с изменениями: фиксируется в Git.
- Тег версии: `v0.2.0-audit-20260220`.

### 4.2 Snapshot
Архив полного снимка проекта в `backup_integrator_20260220_####.zip`.

### 4.3 Переменные окружения и секреты
Переменные окружения описаны в `.env.example`.
Секреты не хранятся в репозитории.

## 5. Дополнение (2026-03-04): фиксация рекомендаций по открытию сессии

### 5.1 Что зафиксировано
- Добавлен операционный раздел «Открытие сессии» в `OPERATIONS_QUICKSTART.md`.
- Зафиксирована команда запуска: `python -m integrator session open --json`.
- Зафиксирован JSON-контракт для автоматизации: `success`, `path`, `path_masked`.
- Зафиксировано правило автоматизации: проверка полей JSON вместо парсинга табличного вывода.

### 5.2 Где закреплено
- `OPERATIONS_QUICKSTART.md` — исполнимые рекомендации для операторского запуска.
- `docs/DOCS_INDEX.md` — индексная ссылка на quickstart как каноничную точку входа.
