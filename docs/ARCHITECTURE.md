# Architecture

## Цели и ограничения
- CLI работает по локальной файловой системе, без сети по умолчанию.
- Массовые операции должны быть предсказуемыми, с устойчивым форматированием вывода.
- Форматы вывода:
  - Табличный вывод по умолчанию (TSV).
  - `--json`: JSONL (1 JSON-объект на строку).
  - `run --json --json-strict`: в `stdout` только JSONL, вывод дочерних команд в `stderr`.

## Точки входа
- `python -m integrator` → [__main__.py](../__main__.py) → `app.run(argv)` → [cli.py](../cli.py).
- Установка entrypoint `integrator` → [pyproject.toml](../pyproject.toml) (`project.scripts`).

## Модули и ответственность
- CLI-роутер:
  - [cli.py](../cli.py): сборка `argparse` дерева и вызов `args.func(args)`.
  - Командные модули:
    - [cli_cmd_misc.py](../cli_cmd_misc.py): `doctor/diagnostics/preflight/exec/rg/registry/chains`.
    - [cli_cmd_projects.py](../cli_cmd_projects.py): `projects list|scan|info`.
    - [cli_cmd_git.py](../cli_cmd_git.py): `status/remotes/report/git bootstrap-ignore`.
    - [cli_cmd_agents.py](../cli_cmd_agents.py): `agents list|status`.
    - [cli_cmd_run.py](../cli_cmd_run.py): `run lint|test|build` (план + опциональный запуск).
    - [cli_cmd_localai.py](../cli_cmd_localai.py): `localai list|assistant ...`.
  - Расширения CLI:
    - [cli_quality.py](../cli_quality.py): `quality summary`.
    - [cli_workflow.py](../cli_workflow.py): `workflow preflight-memory-report`.

- Discovery проектов:
  - [scan.py](../scan.py): обход roots (`os.scandir`), маркеры проектов (`.git`, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `*.sln`), пропуск тяжёлых директорий, agent-aware discovery.

- Git операции (без сети):
  - [git_ops.py](../git_ops.py): `git status -sb --porcelain`, `remote.origin.url`, нормализация GitHub URL.

- Параллелизм:
  - [cli_parallel.py](../cli_parallel.py): единый `ThreadPoolExecutor` map для git/agent проектов, устойчивость к исключениям через `WorkerError`.

- Планирование preset-команд:
  - [run_ops.py](../run_ops.py): `plan_preset_commands(...)` по kind проекта.

- Agent диагностика:
  - [agents_ops.py](../agents_ops.py): построение row с проблемами и подсказками исправления (`--fix-hints`).

- Сервисы (LocalAI/LM Studio preflight):
  - [services_preflight.py](../services_preflight.py): HTTP health-check и опциональный запуск процессов.

- Общие утилиты:
  - [utils.py](../utils.py): печать JSONL/TSV, запуск команд, атомарная запись, файловые проверки.

## Основные потоки данных

### Projects discovery → команды
1) CLI получает `roots/max_depth/project/limit/strict-roots`.
2) `scan.iter_projects` возвращает отсортированный список проектов.
3) Команда обогащает данные (kind/git/agents) и печатает строки (TSV) или JSONL.

### Git status/remotes/report
1) Отбор проектов с `.git`.
2) Параллельное выполнение git операций через [cli_parallel.py](../cli_parallel.py).
3) Формирование строк статуса/remote/репорта.

### Run presets
1) Для каждого проекта строится план (`run_ops.plan_preset_commands`).
2) План печатается (TSV/JSONL).
3) При `--dry-run` выполнение не происходит, при запуске коды возврата агрегируются.

## Критерии совместимости (контракты)
- Имя CLI в help всегда `integrator`.
- `--json` всегда выдаёт JSONL (не массив).
- Массовые операции используют единый `--limit` и стабильную сортировку.
- Ошибки в параллельных worker-функциях не приводят к аварийному завершению команды.

