# Agents.md (for this project)

## Scope
- Project root: `C:\Users\egork\Documents\trae_projects\integrator`
- Core code: `*.py` в корне проекта
- Tests: `tests/`
- Project rules/memory/skills: `.trae/`

## Assistant Rules
- Отвечать по-русски, если пользователь явно не просит иначе.
- Подход: Тезис -> Антитезис -> Синтез.
- Любое утверждение о работоспособности подтверждать командами/тестами/логами.
- Не выполнять разрушительные действия без явного запроса.
- Секреты не писать в код/логи/отчёты.
- Временные ограничения сессии (лимит токенов/времени) считать только текущим контекстом.
- Не фиксировать сессионные лимиты в постоянной документации, если пользователь не попросил явно.

## Default Workflow
1. Сначала быстрый preflight.
2. Затем минимальные изменения с максимальной пользой.
3. После изменений обязательная валидация quality gates.
4. В конце краткий changelog с путями и фактами проверок.

## Preflight Commands
- `python -m integrator doctor`
- `python -m integrator projects list --max-depth 4`
- `python -m integrator agents list --json --roots C:\LocalAI --max-depth 4`
- `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`

## Key CLI Contracts
- Табличный вывод по умолчанию.
- `--json`: JSON object per line.
- `run --json --json-strict`: в `stdout` только JSONL, вывод дочерних команд в `stderr`.
- `agents status --only-problems`: выводит только проблемные agent-проекты.

## Problem Semantics (`agents status`)
- Возможные источники проблем:
- `git_error`, `git_tool-missing`
- `gateway_base_missing`, `gateway_unreachable`, `gateway_routes_missing`
- `media_root_empty|missing`, `work_root_empty|missing`, `publish_root_empty|missing`

## Quality Gates
- `python -m ruff check .`
- `python -m mypy . tests`
- `python -m unittest discover -s tests -p "test*.py"`

## Active Technical Debt
- `app.py` остаётся крупным модулем; следующий этап — модульная декомпозиция.
- В окружении могут встречаться ACL-аномалии во временных папках.

## Post-Reset Plan
1. Разбить `app.py` на модули (`scan.py`, `git_ops.py`, `agents_ops.py`, `run_ops.py`, `cli.py`) без изменения поведения.
2. Добавить `agents status --only-problems --fix-hints` (подсказки команд для проблем, без авто-исправлений).
3. Ввести строгий preflight roots: статусы `ok/missing/access_denied` и флаг `--strict-roots` для batch-команд.
4. Оформить `OPERATIONS_QUICKSTART.md` и добавить smoke-тесты (discovery, only-problems, json-strict).
