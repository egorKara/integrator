## ✅ Obsidian eval: allowlist + explicit enable

- Добавлена команда: `integrator obsidian eval --profile <name> [--vault ...] [--obsidian-bin ...]`
- По умолчанию отключено: без `--enable-eval` возвращает `status=disabled` и exit code 1.
- Разрешены только фиксированные профили (allowlist), свободный `--code` не поддерживается.
- Реализация: [cli_cmd_obsidian.py](file:///C:/integrator/cli_cmd_obsidian.py)
- Тест: [test_obsidian_cli.py](file:///C:/integrator/tests/test_obsidian_cli.py)
