# Code Review Policy

## Цели
- Снизить риск регрессий в CLI и формате вывода.
- Удерживать качество и воспроизводимость (lint/typecheck/tests/coverage).
- Не допускать попадания секретов и содержимого `vault/` в VCS.

## Минимальные требования к PR
- CI зелёный (ruff, mypy, unittest, coverage ≥ 80%).
- Минимум 2 апрува (не считая автора).
- Все замечания закрыты или явно зафиксированы как follow-up задачи.

## Чек-лист ревьюера
- Контракт CLI не сломан:
  - `--json`: строго JSONL (1 объект на строку).
  - `--json --json-strict`: `stdout` только JSONL, вывод дочерних команд уходит в `stderr`.
- Изменения покрыты тестами (unit/integration по месту).
- Нет “тихих” зависимостей от `vault/`, `.tmp/`, локальных абсолютных путей.
- Документация обновлена, есть понятный порядок отката.

## Ресурсы/инструменты
- Локальные проверки:
  - `python -m ruff check .`
  - `python -m mypy .`
  - `python -m unittest discover -s tests -p "test*.py"`
  - `python -m coverage report -m --fail-under=80`

## Настройка репозитория (админ)
- Включить Branch Protection для `main`:
  - Require pull request reviews before merging.
  - Required approvals: 2.
  - Require status checks to pass before merging (ci/test).
  - Dismiss stale approvals on new commits.
- Автоматизация через GitHub API: `python tools/apply_branch_protection.py` (нужны `GITHUB_REPOSITORY` и `GITHUB_TOKEN`).
