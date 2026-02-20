# Changelog
Все заметные изменения проекта документируются в этом файле.

Формат основан на Keep a Changelog, версия следует SemVer.

## [Unreleased]
### Added
- CI-конвейер (GitHub Actions): ruff, mypy, unittest, coverage gate (≥ 80%).
- Процесс code-review и шаблон PR.
- Целевые unit-тесты для `utils.py` (покрытие `utils.py` поднято до 96%).

### Fixed
- Git preflight больше не зависит от родительского репозитория (корректная обработка `.git`).

## [0.2.0] - 2026-02-20
### Added
- Базовый CLI для диагностики, статуса, отчётов, агентных проектов.

