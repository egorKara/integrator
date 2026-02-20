# План выполнения рекомендаций (2026-02-20)

Источник рекомендаций: `reports/audit_conclusion_2026-02-20.md` (раздел `## Recommendations`).

## 1) План работ (ответственные/сроки/ресурсы)

| ID | Приоритет | Рекомендация / действие | Ответственный | Срок | Ресурсы |
|---|---|---|---|---|---|
| P0-1 | Blocker | Исключить `.tmp/` из Git/Ruff/Mypy (устранить недетерминизм) | egork (Dev) | Done | repo, права на рабочую папку |
| P0-2 | Blocker | Зафиксировать исключение `vault/` из типизации/линтинга | egork (Dev) | Done | pyproject.toml, .gitignore |
| P1-1 | Major | Разделить зависимости: проектные (CLI) vs операторские | egork (Dev) | Done | pyproject.toml, requirements*.txt |
| P1-2 | Major | Формализовать quality gate (ruff/mypy/unittest/coverage), стабильный локально | egork (Dev) | Done | ruff/mypy/coverage, tests |
| P1-3 | Major | Детерминированный JSON-отчёт security check в `reports/` | egork (Ops) | Done | .trae/automation, reports/ |
| P1-4 | Major | Добавить CI-конвейер и закрепить gate в PR/merge | egork (DevOps) | 2026-02-21 | GitHub Actions, доступ к настройкам репозитория |
| P2-1 | Minor | Декомпозировать `cli.py` без смены поведения + тесты | egork (Dev) | Done | cli_*.py, tests |
| P2-2 | Minor | Поднять покрытие `run_ops.py` и `agents_ops.py` | egork (Dev) | Done | tests, coverage |
| PROC-1 | Major | Ввести процесс code-review (2 апрува, обязательные checks) | egork (Maintainer) + 2 ревьюера | 2026-02-22 | GitHub Branch Protection, CODEOWNERS |
| DOC-1 | Major | Обновить документацию и порядок отката | egork (Dev) | 2026-02-22 | README, CHANGELOG, docs/ |

## 2) KPI и фиксация результата

| ID | KPI (критерии успеха) | Фиксация результата |
|---|---|---|
| P0-1 | В проверках нет ошибок доступа/ACL из `.tmp/` | отчёт `reports/audit_conclusion_2026-02-20.md` + чистый `git status` |
| P0-2 | `vault/` исключён из ruff/mypy, секреты не трекаются | `pyproject.toml`, `.gitignore`, `git ls-files` без `.env` |
| P1-1 | `requirements.txt` не содержит операторских зависимостей | diff файлов зависимостей + README |
| P1-2 | Gates выполняются локально и в CI; coverage ≥ 80% | CI run, `coverage report --fail-under=80`, `reports/coverage.xml` |
| P1-3 | Security check выдаёт JSON и сохраняется в `reports/` | файл `reports/security_quick_check_*.json` |
| P1-4 | CI запускается на PR и push в main, зелёный | `.github/workflows/ci.yml` + скриншот/ссылка на CI run |
| PROC-1 | ≥ 2 апрува, все замечания закрыты, checks required | скриншот/ссылка на PR, настройки Branch Protection |
| DOC-1 | README/CHANGELOG/docs обновлены, есть rollback шаги | PR/diff + ссылки на документы |

## 3) Риски и меры
- Отсутствие удалённого репозитория/CI: требуется подключение GitHub и включение Actions (DevOps/админ).
- Требование “2 апрува”: необходимо назначить двух ревьюеров и включить Branch Protection (админ).
