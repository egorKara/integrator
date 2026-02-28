## ✅ EPIC: Obsidian CLI (integrator/LocalAI)

Выполнено (по атомарным задачам EPIC):
- `integrator obsidian doctor` (read-only) + тесты.
- `integrator obsidian search` и `integrator obsidian tags counts` (read-only) + тесты.
- `integrator obsidian attachments report` (read-only) и `attachments delete --apply` (write) + тесты.
- `integrator obsidian eval` (disabled by default) с `--enable-eval` и allowlist профилей + тесты.
- SSOT/операционные доки обновлены.

### Верификация
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest tests.test_obsidian_cli` (OK)
