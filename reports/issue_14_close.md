## ✅ integrator obsidian doctor (read-only)

- Добавлена команда: `integrator obsidian doctor [--vault-root ...] [--obsidian-bin ...] [--json]`
- Поля JSON: `obsidian_cli_present`, `obsidian_version`, `vault_root`, `vault_markers`, `status`.
- Реализация: [cli_cmd_obsidian.py](file:///C:/integrator/cli_cmd_obsidian.py)
- Тесты: [test_obsidian_cli.py](file:///C:/integrator/tests/test_obsidian_cli.py)

### Проверки
- `python -m unittest tests.test_obsidian_cli` (OK)
