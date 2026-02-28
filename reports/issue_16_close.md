## ✅ Obsidian attachments: report + delete --apply

- Добавлен отчёт orphan attachments: `integrator obsidian attachments report --vault-root ... --reports-dir ... --json`
  - Пишет `obsidian_attachments_report_*.json` и печатает JSONL (summary + candidates).
- Добавлено удаление только по отчёту: `integrator obsidian attachments delete --report-json ... --backup-dir ... --apply --json`
  - Перед удалением делает копию в `--backup-dir`, затем удаляет файлы внутри vault.
- Реализация: [cli_cmd_obsidian.py](file:///C:/integrator/cli_cmd_obsidian.py)
- Тесты (temp vault, report+delete): [test_obsidian_cli.py](file:///C:/integrator/tests/test_obsidian_cli.py)
