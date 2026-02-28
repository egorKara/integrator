## ✅ integrator obsidian search + tags (read-only)

- Добавлена команда поиска: `integrator obsidian search --query "..." [--limit N] [--vault ...] --json`
  - JSONL: `obsidian_search_result` + `obsidian_search_summary`.
- Добавлена команда метрик тегов: `integrator obsidian tags counts [--vault ...] --json`
  - JSONL: `obsidian_tag_count` + `obsidian_tags_summary`.
- Реализация: [cli_cmd_obsidian.py](file:///C:/integrator/cli_cmd_obsidian.py)
- Тесты: [test_obsidian_cli.py](file:///C:/integrator/tests/test_obsidian_cli.py)

### Проверки
- `python -m unittest tests.test_obsidian_cli` (OK)
