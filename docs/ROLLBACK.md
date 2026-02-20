# Rollback Guide

## Что считается откатом
Откат — возвращение репозитория к состоянию, в котором:
- CLI-контракты и quality gates проходят;
- отсутствуют новые конфиги/правила, вызвавшие сбой в CI/процессе.

## Быстрый откат (Git)
1) Найти merge-коммит или коммит-источник проблемы:
   - `git log --oneline --decorate -n 20`
2) Сделать revert merge-коммита (без переписывания истории):
   - `git revert -m 1 <merge_sha>`
3) Прогнать gates локально:
   - `python -m ruff check .`
   - `python -m mypy .`
   - `python -m unittest discover -s tests -p "test*.py"`
   - `python -m coverage report -m --fail-under=80`

## Откат изменений процесса (CI / Review)
- CI (GitHub Actions):
  - удалить/откатить `.github/workflows/ci.yml` revert-коммитом;
  - при необходимости временно снять обязательность статус-чеков в Branch Protection (админ).
- Code review:
  - требования 2 апрува/branch protection меняются в настройках репозитория (админ);
  - файлы `.github/CODEOWNERS` и `pull_request_template.md` откатываются revert-коммитом.

## Восстановление после отката
- Открыть follow-up задачу с причиной отката и ссылкой на revert-коммит.
- Зафиксировать план исправления и критерии готовности (KPI) в отчёте `reports/`.
