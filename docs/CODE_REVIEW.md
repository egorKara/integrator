# Code Review Policy

## Цели
- Снизить риск регрессий в CLI и формате вывода.
- Удерживать качество и воспроизводимость (lint/typecheck/tests/coverage).
- Не допускать попадания секретов и содержимого `vault/` в VCS.

## Минимальные требования к PR
- CI зелёный (ruff, mypy, unittest, coverage ≥ 80%).
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
- AI-ревьюеры (внутренние специалисты без внешних GitHub reviewers):
  - `.trae/skills/github-pr-reviewer/SKILL.md`
  - `.trae/skills/github-security-reviewer/SKILL.md`

## Настройка репозитория (админ)
- Включить Branch Protection для `main`:
  - Require pull request reviews before merging.
  - Required approvals: 2.
  - Require status checks to pass before merging (`ci / test`).
  - Dismiss stale approvals on new commits.
- Автоматизация через GitHub API: `python tools/apply_branch_protection.py` (нужны `GITHUB_REPOSITORY` и токен: `GITHUB_TOKEN`/`GH_TOKEN` или `GITHUB_TOKEN_FILE`/`INTEGRATOR_GITHUB_TOKEN_FILE`); для безопасной проверки доступа используйте `python tools/apply_branch_protection.py --check-only`.

## Runbook: public-readiness → apply branch protection
- Шаг 1 (внутренний): подтвердить readiness-артефакт
  - `python -m integrator quality public-readiness --json`
- Шаг 2 (внешний): в GitHub Settings перевести репозиторий в `public` (если `PROC-1` заблокирован ограничением тарифа/visibility).
- Шаг 3 (внутренний): проверить доступ к API без изменений
  - `python tools/apply_branch_protection.py --check-only`
- Шаг 4 (внутренний): применить защиту ветки
  - `python tools/apply_branch_protection.py`

## Требования к токену для Branch Protection API
- Классический PAT:
  - scope `repo` (для приватного репозитория).
  - пользователь токена должен быть админом репозитория.
- Fine-grained PAT:
  - Repository access: `egorKara/integrator`.
  - Repository permissions: `Administration = Read and write`, `Contents = Read and write`, `Pull requests = Read and write`.
- GitHub App token:
  - Repository permission `Administration: write`.

## Куда добавить токен в Integrator
- Приоритет загрузки токена:
  1) env: `GITHUB_TOKEN` или `GH_TOKEN`
  2) файл из env: `GITHUB_TOKEN_FILE` или `INTEGRATOR_GITHUB_TOKEN_FILE`
  3) файл по умолчанию: `%USERPROFILE%\\.integrator\\secrets\\github_token.txt`
  4) `.env` в корне репозитория (`GITHUB_TOKEN=...`)
- Рекомендуемый вариант:
  - `C:\\Users\\<user>\\.integrator\\secrets\\github_token.txt` (один токен в отдельном файле).
