# Memory Task (T+A=S)

## Тезис (ситуация)
- Требуется доступ к приватным GitHub репозиториям через REST API без 404 из‑за отсутствия аутентификации.
- Требуется долговременная “оперативная память” задач для агента через GitHub Issues + агрегирование через GitHub Projects.

## Антитезис (проблема/риски/неизвестное)
- Приватные репозитории и часть эндпоинтов при отсутствии/недостатке прав возвращают `404` и выглядят как “repo не существует”.
- Утечки токенов в логи/артефакты недопустимы.
- В core-командах `integrator` нет интеграции с GitHub Issues/Projects; есть только канон/шаблоны в `.github/`.

## Синтез (решение/подход)
- Вынести общий REST-клиент GitHub с безопасным извлечением токена и обязательными заголовками.
- Для проверки доступа к приватному repo добавить режим “только проверка” без мутаций.
- Зафиксировать процесс “issue как промпт/память” и “project как агрегатор” в документации, опираясь на канон.
- Добавить портативный скрипт (без установки gh CLI) для create/comment/close issue через GitHub REST API.

## Контекст
- Репо/модуль: `integrator`
- Цель: безопасная авторизация GitHub REST API + инструмент “issue как память задачи”
- Ограничения/инварианты:
  - секреты только в env/.env (не коммитить, не печатать в логи)
  - доказательства verify без секретов
- Связанные материалы:
  - Канон: `.github/PROJECT_CANON.md`
  - Шаблон: `.github/ISSUE_TEMPLATE/memory-task.yml`
  - Источник: https://sereja.tech/blog/github-projects-ai-agent-memory/
  - GitHub REST API auth: https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api

## Текущее состояние
- Сделано:
  - Добавлен общий GitHub REST клиент: `github_api.py`
  - Обновлён `tools/apply_branch_protection.py`: precheck доступа + `--check-only`
  - Добавлена документация: `docs/GITHUB_API_AUTH.md`, `docs/GITHUB_ISSUES_PROJECTS_MEMORY.md` + ссылка в `docs/DOCS_INDEX.md`
  - Добавлен портативный tool для issue: `tools/gh_issue_memory.py` + `github_issues.py`
  - Добавлены unit-тесты: `tests/test_github_api.py`, `tests/test_github_issues.py`
- Осталось:
  - Добавить созданную issue в общий GitHub Project и вести статусы по канону.
- Блокеры:
  - Нет

## SSOT / Knowledge impact
- Link: `docs/GITHUB_API_AUTH.md`, `docs/GITHUB_ISSUES_PROJECTS_MEMORY.md`
- Update: актуализировать при добавлении интеграции Projects API/GraphQL (если потребуется)

## Верификация
Ожидаемое поведение:
- GitHub REST API запросы к приватному repo выполняются с `Authorization` и не маскируются как 404 из‑за отсутствия аутентификации.
- Создание/комментирование/закрытие issue выполняется портативным скриптом без утечки токена в stdout/stderr.

Чеки:
- lint: `python -m ruff check .`
- tests: `python -m unittest discover -s tests -p "test*.py"`
- typecheck: `python -m mypy .`
- smoke/manual:
  - `python tools/apply_branch_protection.py --check-only`
  - `python tools/gh_issue_memory.py create ...`
  - `python tools/gh_issue_memory.py comment ...`
  - `python tools/gh_issue_memory.py close ...`
- регрессии:
  - `parse_repo_slug` корректно парсит `https://github.com/owner/repo.git` и `git@github.com:owner/repo.git`

Доказательства (без секретов):
- Ссылки на файлы: `github_api.py`, `tools/apply_branch_protection.py`, `tools/gh_issue_memory.py`, `github_issues.py`
- Отчёты создаются в `reports/*.json` (без значения токена)

## План отката
- `git restore --source=HEAD -- github_api.py github_issues.py tools/apply_branch_protection.py tools/gh_issue_memory.py docs/GITHUB_API_AUTH.md docs/GITHUB_ISSUES_PROJECTS_MEMORY.md docs/DOCS_INDEX.md`
- `git clean -f -- tests/test_github_api.py tests/test_github_issues.py docs/issue_memory_task_github_auth_and_memory.md`

## Next atomic step
Добавить эту issue в GitHub Project и проставить поля Status/Type/Priority/Verification.
