# Integrator Audit + Development Plan (2026-02-18)

## 1) Контекст и цель
- Объект аудита: `C:\Users\egork\Documents\trae_projects\integrator`
- Цель: тщательный аудит качества и рекомендации по развитию с учётом активных агентов и связанных проектов.
- Метод: Тезис + Антитезис = Синтез.

## 2) Что было прочитано и проверено
### 2.1 Основные файлы integrator
- `README.md`
- `pyproject.toml`
- `integrator/__init__.py`
- `integrator/__main__.py`
- `integrator/app.py`
- `tests/test_smoke.py`
- `tests/test_projects.py`

### 2.2 Агентные файлы integrator (.trae)
- `.trae/rules/project_rules.md`
- `.trae/memory/project_memory.xml`
- `.trae/automation/security_quick_check.ps1`
- `.trae/global_gitignore_localai`
- `.trae/skills/*/SKILL.md`

### 2.3 Связанный проект LocalAI assistant
- `C:\LocalAI\assistant\.trae\rules\project_rules.md`
- `C:\LocalAI\assistant\.trae\rules\global_rules.md`
- `C:\LocalAI\assistant\.trae\memory\project_memory.xml`
- `C:\LocalAI\assistant\.trae\skills\*/SKILL.md`
- `C:\LocalAI\assistant\Check-ProjectStatus.ps1`
- `C:\LocalAI\assistant\README.md`
- `C:\LocalAI\assistant\README-Run.md`
- `C:\LocalAI\assistant\projects\agent_gateway\config\gateway.json`
- `C:\LocalAI\assistant\projects\media_storage\config\media_paths.json`
- Скрипты `C:\LocalAI\assistant\projects\agent_gateway\scripts\*.ps1`

## 3) Фактическая картина (Тезис)
### 3.1 По integrator
- Архитектура CLI единая, но ядро монолитно (`integrator/app.py`, ~720 строк).
- Stdlib-first подход сохранён.
- Команды: `doctor`, `projects`, `status`, `remotes`, `run`, `localai`, `report`, `exec`.
- Вывод поддерживает табличный и JSON режим.

### 3.2 По агентной среде
- В `integrator` активны skills: `integrator-cli-engineer`, `localai-assistant-ops`, `security-ops`, `vpn-manager-fedora-maintainer`, `claude-stealth-connect-ops`.
- В `C:\LocalAI\assistant` активны 9 skills (в т.ч. `rag-diagnostics`, `memory-manager`, `metrics-manager`, `test-generator`).
- В `assistant` есть подпроекты `projects/agent_gateway` и `projects/media_storage` с отдельными operational-скриптами.

### 3.3 По связанным roots
- `C:\LocalAI` доступен.
- `C:\vault\Projects` и вложенные пути в этой сессии недоступны (Access Denied), поэтому аудит связей с ними ограничен.

### 3.4 Фактические данные состояния
- `python -m integrator doctor`:
  - root `C:\vault\Projects` -> `exists=False`
  - root `C:\LocalAI` -> `exists=True`
- `python -m integrator report --json --roots C:\LocalAI --max-depth 2`:
  - project `assistant`
  - `state=dirty`, `changed=2076`, `untracked=44`

### 3.5 Порты/сервисы в момент проверки
- `8000` (RAG): not listening
- `8011` (agent gateway): not listening

## 4) Критические противоречия и риски (Антитезис)
1. JSON-режим `run` до доработки был нестрогим: stdout дочерних команд смешивался с JSON.
2. При отсутствии `git` CLI мог падать traceback в `status/remotes/report`.
3. Резолв интерпретатора Python без фильтра мог выбирать `WindowsApps\python.exe` (Store alias), что ломает запуск.
4. Тесты зависели от `tempfile.TemporaryDirectory()`, который в данной среде воспроизводимо падал на ACL/PermissionError.
5. Обнаружение проектов в `integrator` не охватывает часть агентных подпроектов без стандартных marker-файлов (например, чисто config/scripts-папки).
6. Репозиторий `assistant` сильно загрязнён (много changed/untracked), что повышает риск batch-операций.

## 5) Синтез: принятые технические решения и изменения

### 5.1 Изменения в коде (выполнено)
#### Файл: `integrator/app.py`
- Добавлен безопасный запуск внешних команд:
  - `_run_command(...)` теперь обрабатывает `FileNotFoundError` и возвращает `127` вместо падения.
  - `_run_capture(...)` теперь безопасно возвращает ошибки (`127`, `tool not found: ...`) и не кидает traceback наружу.
- Добавлен строгий режим JSON для `run`:
  - Новый флаг `--json-strict` (для подкоманды `run`).
  - Контракт: при `--json --json-strict` в `stdout` только JSONL, а вывод дочерних процессов уходит в `stderr`.
  - Проверка аргументов: `--json-strict` требует `--json`.
- Улучшена деградация при отсутствии git:
  - `state` теперь может быть `tool-missing` и `error` (помимо `clean`/`dirty`).
  - `status` не падает traceback, а возвращает структурированное состояние.
- Улучшен резолв Python-интерпретатора:
  - `_resolve_python_command(...)`.
  - Приоритет: локальные env (`env312/.venv/venv`) -> `sys.executable` -> валидный `python`/`python3` из PATH.
  - Исключён выбор `WindowsApps\python.exe` alias.
- Локальные команды `localai assistant mcp/rag` теперь используют резолвер Python, а не жёсткий `python`.
- Для Python-проектов `plan_preset_commands(...)` использует резолвер Python и более надёжный выбор `pytest`.

#### Файл: `README.md`
- Добавлен пример `run ... --json --json-strict`.
- Добавлено пояснение контракта stdout/stderr для машинного парсинга.

### 5.2 Изменения в тестах (выполнено)
#### Файл: `tests/test_projects.py`
- Удалена зависимость от `tempfile.TemporaryDirectory`.
- Добавлен собственный fixture `project_case_dir()` на основе создаваемых/удаляемых директорий в `tests`.
- Добавлены новые тесты:
  - `test_status_json_reports_tool_missing`
  - `test_run_json_strict_keeps_stdout_jsonl`
  - `test_run_json_strict_requires_json`
- Адаптирован тест планирования Python-команд к новому резолву интерпретатора.

## 6) Верификация изменений (проверено)
- `python -m ruff check .` -> passed
- `python -m mypy integrator tests` -> passed
- `python -m unittest discover -s tests -p 'test*.py'` -> passed (15 tests)

### Точечные runtime-проверки
- `run test --json --json-strict --cwd <integrator>`:
  - `stdout`: ровно JSONL-строка
  - `stderr`: вывод unittest
  - exit code `0`
- `status --json` без `git` в PATH:
  - не падает traceback
  - возвращает `state: tool-missing`
  - exit code `1`

## 7) Рекомендации дальнейшего развития (TAS roadmap)
### P0 (сделано в этом цикле)
- JSON strict output для batch/automation.
- Graceful fallback при missing tools.
- Надёжный Python resolver.

### P1 (следующий шаг)
1. Agent-aware discovery:
- Добавить реестр/маркеры для подпроектов вида `config+scripts` (например `agent_gateway`, `media_storage`), чтобы `integrator` видел их явно.
2. Root health contracts:
- Явно различать `missing` и `access_denied` для roots.
- Флаг строгого режима по roots.
3. Git hygiene automation:
- Команда bootstrap для `.gitignore` (на основе `.trae/global_gitignore_localai`).
- Preflight-check “грязности” перед массовыми `run`.

### P2
1. Декомпозиция `integrator/app.py`:
- Разнести parser/scan/git/run/output в отдельные модули.
2. Observability:
- Единый machine-readable отчёт об ошибках инструментов/доступа.

### Векторы развития
- Интегрировать реестр проектов как источник roots и добавить цепочки управления через integrator.
- Вычленить похожие по функционалу скрипты из всех проектов в общую библиотеку.
- Ввести пул задач для последующего планирования расхода контекста.
- Исследовать внешние базы библиотек Python (PyPI/Libraries.io/conda‑forge) и интегрировать в аналитику.
- Закрепить правило: все входящие сообщения разбиваются на задачи/векторы/правила с оценкой и режимом (сразу/позже/параллельно) с Т+А=С при необходимости.

## 8) Ограничения и хвосты
- В этой сессии недоступны пути `C:\vault\Projects*` (Access Denied), поэтому часть связей проверена только по конфигам/skill-файлам.
- Остались служебные диагностические папки с проблемными ACL (созданы в ходе исследования среды `tempfile`):
  - `C:\Users\egork\Documents\trae_projects\integrator\sandbox_tmp_check`
  - `C:\Users\egork\Documents\trae_projects\integrator\sandbox_tmp_check3`

## 9) Какие файлы были изменены в рамках реализации
- `C:\Users\egork\Documents\trae_projects\integrator\integrator\app.py`
- `C:\Users\egork\Documents\trae_projects\integrator\tests\test_projects.py`
- `C:\Users\egork\Documents\trae_projects\integrator\README.md`

## 10) Короткий итог
- P0-улучшения реализованы и проверены.
- Тестовый контур стабилизирован для текущего окружения.
- Отчёт сохраняет весь ключевой собранный контекст и результаты проверок.

## 11) Update (P1) — Agent-aware discovery and agents status
Дата/время обновления: 2026-02-18

### Реализовано
1. Agent-aware discovery:
- Директории с маркерами agent-проекта теперь распознаются как проекты.
- Поддержаны случаи с `.trae/rules/project_rules.md` и структурами `config/*.json + scripts/`.

2. Новый раздел CLI `agents`:
- `integrator agents list`
- `integrator agents status`

3. Расширенная диагностика agent-проектов:
- `agent_type`, `kind`, git state, `scripts`, `config_json`
- Для gateway: `gateway_base`, `gateway_routes`, `gateway_up`
- Для media_storage: `media_root/work_root/publish_root` и `*_exists`

4. Дополнено определение `kind`:
- Для таких каталогов `projects info/report` теперь может возвращать `kind=agent`.

### Проверка на реальном окружении
Команда:
`python -m integrator projects list --roots C:\LocalAI --max-depth 4 --limit 20`
Результат (ключевое):
- `assistant`
- `agent_gateway`
- `media_storage`

Команда:
`python -m integrator agents list --json --roots C:\LocalAI --max-depth 4 --limit 30`
Результат (ключевое):
- `agent_gateway` (`agent_type=gateway`)
- `assistant` (`agent_type=trae-project`)
- `media_storage` (`agent_type=media-storage`)

Команда:
`python -m integrator agents status --json --roots C:\LocalAI --max-depth 4 --limit 30`
Результат (ключевое):
- Для `agent_gateway`: считаны gateway-параметры и статус endpoint
- Для `media_storage`: считаны пути media/work/publish и флаги существования

### Тесты/качество
- `ruff check` — passed
- `mypy integrator tests` — passed
- `unittest` — 19 tests, OK

## 12) Update (P1.1) — `agents status --only-problems`
Дата/время обновления: 2026-02-18

### Реализовано
- В `agents status` добавлен флаг `--only-problems`.
- Для каждой строки `agents status` формируется поле `problems`.

### Правила проблем
- Git: `state` в `error|tool-missing`.
- Gateway:
  - `gateway_base_missing`
  - `gateway_unreachable`
  - `gateway_routes_missing`
- Media storage:
  - `media_root_empty|media_root_missing`
  - `work_root_empty|work_root_missing`
  - `publish_root_empty|publish_root_missing`

### Проверка в реальном окружении
Команда:
`python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4 --limit 30`
Результат:
- Выведен только `media_storage` с проблемами:
  - `media_root_missing`
  - `work_root_missing`
  - `publish_root_missing`

### Валидация
- `ruff check` — passed
- `mypy integrator tests` — passed
- `unittest` — 21 tests, OK
