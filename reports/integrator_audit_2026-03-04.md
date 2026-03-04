# Детальный аудит состояния проекта integrator (2026-03-04)

## Параметры аудита
- Объект: репозиторий `c:\integrator`.
- Принцип фиксации: только подтверждённые факты; каждый пункт помечен как `Проверено` / `Не проверено` / `Противоречиво`.
- Временная метка: 2026-03-04 (локальная сессия).

## Срез верификации команд (текущая сессия)
- `git branch --show-current` → `main`.
- `git rev-parse --short HEAD` → `34be959`.
- `git status --short` → подтверждены локальные изменения: 12 modified tracked-файлов и большой пул untracked-артефактов.
- `python -m ruff check .` → `All checks passed!`.
- `python -m mypy .` → `Success: no issues found in 93 source files`.
- `python -m unittest discover -s tests -p "test*.py"` → `Ran 196 tests`, `OK`.

## 1) Структура репозитория

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Базовые каталоги присутствуют | Проверено | Листинг корня показывает `.github`, `.trae`, `docs`, `tests`, `tools`, `scripts`, `reports` и Python-модули в корне. |
| Точка входа CLI | Проверено | `__main__.py` вызывает `app.run`; `app.py` — thin-wrapper, фактический роутинг в `cli.py`. |
| Покрытие команд CLI | Проверено | В `cli.py` зарегистрированы `doctor`, `projects`, `preflight`, `status`, `remotes`, `run`, `agents`, `localai`, `report`, `chains`, `registry`, `perf`, `quality`, `workflow`, `incidents`, `obsidian`, `github`, `hygiene`. |
| Состояние git-рабочего дерева | Проверено | `git status --short` (текущая сессия): 12 modified tracked-файлов и множество untracked-артефактов; ветка `main`, commit `34be959`. |
| Scope-путь в AGENTS.md актуален | Противоречиво | В `AGENTS.md` указан исторический путь `C:\Users\egork\Documents\trae_projects\integrator`, текущий root сессии: `C:\integrator`. |

## 2) Документация: наличие и актуальность

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Есть явный doc-entrypoint | Проверено | `README.md` ссылается на `docs/DOCS_INDEX.md`. |
| DOCS_INDEX покрывает все ключевые документы | Противоречиво | `DOCS_INDEX.md` не включает `ARCHITECTURE.md`, `LLM_SIDECAR.md`, `INCIDENTS.md`, `CODE_REVIEW.md`, хотя файлы существуют. |
| Инцидентная документация связана корректно | Проверено | `docs/INCIDENTS.md` ссылается на существующие `INCIDENT_TEMPLATE.md` и файл инцидента в `docs/incidents`. |
| Исторические аудиты консистентны с текущим кодом | Противоречиво | В `INTEGRATOR_AUDIT_2026-02-18.md` зафиксирован «монолит app.py», но сейчас `app.py` декомпозирован. |
| Есть “битые” тематические ссылки | Проверено | В ряде docs есть упоминания `bhagavad-gita-reprint`; соответствующий каталог в репозитории отсутствует. |

## 3) CI/CD-конвейеры

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| CI workflow присутствует | Проверено | `.github/workflows/ci.yml` найден и активируется на `push`/`pull_request` в `main`. |
| Release workflow присутствует | Проверено | `.github/workflows/release.yml` найден, активируется по тегам `v*.*.*`. |
| CI quality-gates формализованы | Проверено | В `ci.yml`: `ruff`, `mypy`, `unittest`, `coverage --fail-under=80`. |
| Security-gates формализованы | Проверено | В `ci.yml`: `gitleaks` + `pip-audit` (`requirements.txt` и `requirements.operator.txt`) с artifacts. |
| Текущий online-статус последних запусков CI | Проверено | Подтверждены 3 последовательных успешных run workflow `ci`: `22667303376`, `22667203128`, `22667085946` (`conclusion=success`). |
| Branch protection реально включён | Не проверено | В рамках текущего аудита не запрашивались настройки protection rules через API/GUI. |

## 4) Тесты и покрытие

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Unit-тесты присутствуют | Проверено | Каталог `tests/` содержит 30+ файлов тестов по подсистемам. |
| Локальный прогон тестов | Проверено | `python -m unittest discover -s tests -p "test*.py"`: `Ran 196 tests`, `OK` (текущая сессия). |
| Локальный lint gate (ruff) | Проверено | Команда `python -m ruff check .` завершилась успешно: `All checks passed!`. |
| Локальный typecheck gate (mypy) | Проверено | Команда `python -m mypy .` завершилась успешно: `Success: no issues found in 93 source files`. |
| Локальный coverage-gate | Проверено | `python -m coverage run ... && python -m coverage report --fail-under=80` завершился с кодом 0. |
| Общее покрытие | Проверено | По локальному отчёту `TOTAL 84%`, порог CI `>=80%` выполнен. |
| Узкие места покрытия | Проверено | Модули ниже 80%: `cli_cmd_algotrading.py`, `cli_cmd_localai.py`, `cli_cmd_misc.py`, `cli_cmd_obsidian.py`, `cli_env.py`, `cli_quality.py`, `github_api.py`, `guardrails.py`, `services_preflight.py`, `tools/lm_studio_sidecar.py`, `tslab_offline_csv.py`, `scripts/validate_tslab_finam_txt.py`. |

## 5) Issues и Pull Requests

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Remote на GitHub настроен | Проверено | `git remote -v`: `origin https://github.com/egorKara/integrator.git`. |
| Доступ к API репозитория подтверждён | Проверено | `github_api_request(GET /repos/egorKara/integrator)` вернул `status=200`. |
| Открытые Issues | Проверено | `GET /repos/egorKara/integrator/issues?state=open&per_page=100` → `issues_open_count=0`. |
| Открытые Pull Requests | Проверено | `GET /repos/egorKara/integrator/pulls?state=open&per_page=100` → `pulls_open_count=0`. |
| Полнота issue/PR списка (более 100) | Не проверено | Проверка выполнялась с `per_page=100` без пагинации последующих страниц. |

## 6) Технологии и зависимости

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Язык/платформа | Проверено | Проект на Python, packaging через setuptools (`pyproject.toml`). |
| Поддерживаемая версия Python (декларация) | Проверено | `requires-python = ">=3.10"` в `pyproject.toml`. |
| Версия Python в текущей сессии | Проверено | Командные выводы показывают интерпретатор Python `3.14.2`. |
| Runtime-зависимости пакета | Проверено | `dependencies = []` (stdlib-first модель runtime). |
| Dev-зависимости | Проверено | `build`, `coverage`, `mypy`, `pre-commit`, `ruff`, `twine` определены в `[project.optional-dependencies].dev`. |
| Пинning зависимостей | Противоречиво | `pyproject` использует `>=`, при этом добавлен lock-файл `requirements.dev.lock.txt`; стратегия частично унифицирована, но источники зависимостей остаются смешанными. |
| Operator-окружение | Проверено | `requirements.operator.txt` содержит расширенный pinned-стек (98 пакетов). |

## 7) Метрики производительности и доступности

| Пункт | Статус | Факт подтверждения/опровержения |
|---|---|---|
| Доступность RAG health | Проверено | `python -m integrator preflight --json`: `http://127.0.0.1:8011/health` вернул `200`, `ok=true`. |
| Доступность LM Studio API | Проверено | `python -m integrator preflight --json`: `http://127.0.0.1:1234/v1/models` вернул `200`, `ok=true`. |
| Perf baseline сформирован | Проверено | `python -m integrator perf baseline --json` сохранил `reports/perf_baseline_20260304.json`. |
| Время ключевых команд | Проверено | По baseline: `projects_list ~638 ms`, `status ~685 ms`, `report_json ~351 ms`, `doctor ~182 ms`. |
| Стабильность status в baseline | Проверено | В актуальном baseline `status.any_failed=false`, `perf baseline --roots .` завершается с кодом `0`. |

## Диалектика: тезис → антитезис → синтез

### Тезис (что заявлено в roadmap/todo)
- В `reports/recommendations_followup_plan_2026-02-20.md` заявлены planned-пункты:
  - `P2-CLI-1`: декомпозиция `cli.py` без изменения контрактов.
  - `P2-QUAL-2`: довести покрытие `cli_quality.py` и убрать warning-шум.
  - `P2-ARCH-1`: архитектурное исследование event-driven agents.
- В `AGENTS.md` закреплён техдолг: `cli.py` ещё крупный модуль; низкое покрытие `agent_memory_client.py` и `git_ops.py`.

### Антитезис (контрольные вопросы и фактические ответы)

#### Блок A — CI/CD и качество
1. Выполняются ли в CI формальные quality-gates? — Подтверждено (`ruff/mypy/unittest/coverage>=80`).
2. Есть ли security-gates и артефакты? — Подтверждено (`gitleaks`, `pip-audit`, upload artifacts).
3. Проходит ли CI фактически на последних запусках? — Подтверждено (последние 3 run `ci` завершились `success`: `22667303376`, `22667203128`, `22667085946`).
4. Совпадает ли локальное состояние качества с требованиями CI? — Подтверждено (локально пройдены `unittest`, `ruff`, `mypy`).
5. Подтверждён ли required-check policy (branch protection)? — Не подтверждено в текущем аудите.
6. Есть ли кроссплатформенная проверка? — Подтверждено (`ubuntu` + `windows` jobs в CI).

#### Блок B — Документация и SSOT
1. Есть ли единый вход в документацию? — Подтверждено (`DOCS_INDEX.md`).
2. Полный ли индекс относительно фактических docs? — Опровергнуто (не все ключевые файлы включены).
3. Консистентны ли исторические отчёты с текущим кодом? — Опровергнуто (устаревшие формулировки про `app.py`).
4. Есть ли навигационные следы на отсутствующие сущности? — Подтверждено (упоминания `bhagavad-gita-reprint`).
5. Обновляется ли техдолг в явном виде? — Подтверждено (`AGENTS.md` содержит active debt).
6. Есть ли единый живой roadmap-файл SSOT? — Не подтверждено (дорожные пункты распределены по отчётам).

#### Блок C — Тесты, покрытие и эксплуатационные метрики
1. Есть ли достаточный тестовый контур? — Подтверждено (196 тестов проходят локально).
2. Выполнен ли coverage-порог? — Подтверждено (84% ≥ 80%).
3. Закрыты ли зоны низкого покрытия в CLI/ops-модулях? — Опровергнуто (ряд модулей <80%).
4. Подтверждена ли доступность ключевых сервисов? — Подтверждено (RAG и LM Studio health=200).
5. Есть ли регрессии в perf-профиле команд? — Не подтверждено (актуальный baseline фиксирует `status.any_failed=false`).
6. Есть ли единый публичный SLI/SLO отчёт в docs? — Не подтверждено.

### Синтез
- Приоритетный бэклог с критичностью, трудозатратами и Definition of Done сохранён в:
  - `reports/integrator_priority_backlog_2026-03-04.md`

## Итог по достоверности аудита
- Проверено: структура, docs-файлы, CI/release-конфигурации, локальный прогон unit-тестов (196/OK), данные git-среза текущей сессии.
- Не проверено: branch protection settings, пагинация issues/PR >100, внешние SLA/SLO вне репозитория.
- Противоречиво: часть исторических документов и индексация docs не соответствует текущему состоянию кода/структуры.
