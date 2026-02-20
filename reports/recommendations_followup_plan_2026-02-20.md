# План действий по актуальным рекомендациям (2026-02-20)

Источник: `reports/audit_conclusion_2026-02-20.md`, `reports/project_priorities_2026-02-20.md`, `INTEGRATOR_AUDIT_2026-02-18.md`.

## Тезис
- Цель: формализовать оставшиеся и новые рекомендации (включая sidecar LM Studio), назначить ответственных/ресурсы, KPI и фиксацию результата.

## Антитезис
- Риски: изменения в CI/процессах должны сохранять обратную совместимость и не нарушать контракты CLI (`--json`, `--json-strict`).
- Ограничение: внешние системы (GitHub Branch Protection, ревьюеры) требуют действий вне репозитория; в рамках репозитория фиксируется артефакт и runbook.

## Синтез

### 1) План работ (ответственные/сроки/ресурсы)

| ID | Приоритет | Рекомендация / действие | Ответственный | Срок | Ресурсы | Статус |
|---|---|---|---|---|---|---|
| P0-PROC-1 | Blocker | Включить Branch Protection для `main` и required checks (`ci / test`) + 2 approvals | egork (Maintainer) | 2026-02-21 | GitHub Settings/API, `tools/apply_branch_protection.py` | In progress |
| P0-SEC-1 | Blocker | Security gates в CI: gitleaks + pip-audit, JSON artifacts | egork (DevOps) | Done | GitHub Actions | Done |
| P1-OPS-1 | Major | “preflight → (quality) → (memory-write) → report” как единый сценарий с артефактами | egork (Dev/Ops) | Done | CLI integrator, `reports/` | Done |
| P1-QUAL-1 | Major | `integrator quality summary` (JSON: toolchain+gates+артефакты) | egork (Dev) | Done | CLI integrator | Done |
| P1-LLM-1 | Major | Sidecar под LM Studio: `reports/*.json` → `reports/*.md` (reco/triage/tests) | egork (Ops) | Done | LM Studio server, `tools/` | Done |
| P2-CLI-1 | Minor | Дальнейшая декомпозиция `cli.py` по подсистемам без смены контрактов | egork (Dev) | 2026-02-28 | CLI, tests | Planned |
| P2-QUAL-2 | Minor | Добить покрытие `cli_quality.py` и убрать warning-шум в тестах | egork (Dev) | 2026-02-28 | unittest/coverage | Planned |

### 2) KPI и фиксация результата

| ID | KPI (критерии успеха) | Фиксация результата |
|---|---|---|
| P0-PROC-1 | PR merge невозможен без `ci / test` и 2 approvals | `reports/branch_protection_apply_*.json` + скриншот/экспорт настроек репозитория |
| P0-SEC-1 | CI публикует security artifacts; job падает при находках | CI run + artifacts: `reports/gitleaks.json`, `reports/pip-audit-*.json` |
| P1-OPS-1 | Единый запуск пишет `*.summary.json`, `*.projects.json`, `*.errors.log` | Локальный запуск команды + файлы в `reports/` |
| P1-QUAL-1 | JSON summary стабилен; gates совпадают с CI | `reports/quality_summary*.json` + CI run |
| P1-LLM-1 | Sidecar генерирует 3 отчёта и не требует секретов | `reports/recommendations_llm*.md`, `reports/ci_triage_llm*.md`, `reports/test_suggestions_llm*.md` |
| P2-CLI-1 | Нет изменений контракта `--json`/`--json-strict`, тесты зелёные | unittest + smoke tests + diff ссылок на команды |
| P2-QUAL-2 | Coverage ≥ 80% общий; `cli_quality.py` ≥ 80%; нет ResourceWarning в тестах | `coverage report`, CI logs без warning |
