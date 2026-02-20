# Changelog
Все заметные изменения проекта документируются в этом файле.

Формат основан на Keep a Changelog, версия следует SemVer.

## [Unreleased]
### Added
- CI-конвейер (GitHub Actions): ruff, mypy, unittest, coverage gate (≥ 80%).
- Security gates в CI: gitleaks + pip-audit с JSON artifacts.
- Required check `ci / test` для Branch Protection.
- Процесс code-review и шаблон PR.
- Команды CLI: `quality summary`, `workflow preflight-memory-report`.
- LM Studio sidecar для анализа артефактов `reports/` и генерации отчётов.
- Целевые unit-тесты для `utils.py` (покрытие `utils.py` поднято до 96%).
- Целевые unit-тесты для `agent_memory_client.py` и `git_ops.py` (≈ 87% каждый).

### Fixed
- Git preflight больше не зависит от родительского репозитория (корректная обработка `.git`).

## [0.2.0] - 2026-02-20
### Added
- Базовый CLI для диагностики, статуса, отчётов, агентных проектов.

