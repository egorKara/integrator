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
- RFC `P2-ARCH-1` по event-driven agents: `docs/RFC_P2_ARCH_1_EVENT_DRIVEN_AGENTS_2026-03-04.md`.
- Golden-контракт тесты для `--json/--json-strict` и guard на размер `cli.py` (`tests/test_cli_contracts_golden.py`).

### Fixed
- Git preflight больше не зависит от родительского репозитория (корректная обработка `.git`).
- `quality github-snapshot` теперь публикует и JSON, и Markdown-сводку в `reports/`.
- `perf baseline` поддерживает проверку деградации относительно baseline, добавлен `perf check`.

## [0.2.0] - 2026-02-20
### Added
- Базовый CLI для диагностики, статуса, отчётов, агентных проектов.
