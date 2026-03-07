# Operations Quickstart

## Trae 3.5.35 Workflow Note
- Markdown-отчёты открывайте в Preview (переключение Editor/Preview).
- После запуска команд смотрите вывод в terminal card (авто-открытия терминала больше нет).
- В операционных отчётах фиксируйте путь к артефакту и статус выполнения команды.

## Быстрый старт
- `python -m integrator doctor`
- `python -m integrator diagnostics --only-problems`
- `python -m integrator projects list --max-depth 4`
- `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`
- `python -m integrator registry list`
- `python -m integrator chains list`

## Боевой checklist запуска дня (8 команд)
1. `python -m integrator preflight --check-only --json`
2. `python -m integrator doctor`
3. `python -m integrator projects list --max-depth 4`
4. `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`
5. `python -m integrator quality mcp-tools-inventory --json --write-report reports/mcp_tools_inventory_YYYYMMDD.json`
6. `python -m integrator quality github-snapshot --repo egorKara/integrator --state open --json`
7. `python -m integrator quality projects-migration-readiness --repo egorKara/integrator --json --write-report reports/projects_migration_readiness_YYYYMMDD.json`
8. `python -m integrator report --json`

## Артефакты в репозитории
- `reports/`: отчёты качества, security, перф-бейзлайны и operator-логи (по необходимости).
- `.trae/memory/`: локальные рабочие файлы сессий; в VCS обязателен только `project_memory.xml`.

## Цикл сессии (append-first)
- Основной старт работы: `python -m integrator workflow zapovednik append --role user --text "..." --json`.
- После `workflow zapovednik finalize` следующий `append` без `--path` автоматически создаёт новую сессию.
- Проверка состояния и автокритерия закрытия: `python -m integrator workflow zapovednik health --json`.
- Автозакрытие перед append по порогам: `python -m integrator workflow zapovednik append --auto-finalize-on-threshold --json`.
- Профили порогов `recommend_close`: `--profile research|coding|ops` (по умолчанию `coding`), точечные `--*-limit/--*-ratio` флаги переопределяют профиль.
- Для machine-check использовать поля append JSON: `auto_finalize_triggered`, `recommend_close_before_append`, `auto_finalize_reasons`.
- Стандартное закрытие сессии единым запуском: `python -m integrator session close --json`.
- `python -m integrator session open --json` использовать как fallback для ручного принудительного старта.
- Для `session open` поле `success=true` подтверждает успешное создание/инициализацию сессии.
- Для `session open` поле `path` содержит путь к файлу сессии в `.trae/memory`.
- Для `session open` поле `path_masked=true` означает маскировку чувствительных сегментов пути как `[REDACTED]`.
- Для автоматизации проверять поля JSON (`success`, `path_masked`), а не табличный вывод.

## Статусы репозиториев
- `python -m integrator status --only-dirty`
- `python -m integrator remotes --only-github`
- `python -m integrator report --json`

## Агенты
- `python -m integrator agents list --json --roots C:\LocalAI --max-depth 4`
- `python -m integrator agents status --json --only-problems --fix-hints --roots C:\LocalAI --max-depth 4`

## Память агента (RAG server)
- `python -m integrator localai assistant memory-write --base-url http://127.0.0.1:8011 --content-file C:\path\to\note.md --summary "note"`

## Запуск пресетов
- `python -m integrator run lint --dry-run`
- `python -m integrator run test --json --json-strict --dry-run`
- `python -m integrator run test --json --json-strict --quiet-tools`
- `python -m integrator run build --dry-run`

## GitHub auth precheck
- `python -m integrator quality github-snapshot --repo egorKara/integrator --state open --json`

## Governance и приоритизация
- `python -m integrator quality projects-migration-readiness --repo egorKara/integrator --json`
- `python -m integrator quality github-snapshot --repo egorKara/integrator --state open --json`
- `python -m integrator quality mcp-tools-inventory --json`
- `python -m tools.ensure_daily_priority_template --reports-dir reports --json`

## LocalAI assistant
- `python -m integrator localai list --root C:\LocalAI --max-depth 3`
- `python -m integrator localai assistant rag --cwd C:\LocalAI\assistant`
- `python -m integrator localai assistant rag --cwd C:\LocalAI\assistant --daemon`
- `python -m integrator localai assistant reindex --cwd C:\LocalAI\assistant`

## Git bootstrap ignore
- `python -m integrator git bootstrap-ignore --dry-run`

## Нулевой шум (рабочее дерево)
- `git status --porcelain=v1 -uall`
- Целевое правило: перед стартом цикла и перед отчётом держать `??` под контролем и не копить шумовые артефакты.

## Quality-First Self-Tuning
- `python guardrails.py --strict --json`
- `python ops_checklist.py --json`
- `.\scripts\bootstrap_integrator.ps1 -Profile full -InstallPreCommit -RunChecklist -RunQuality`
- `.\scripts\bootstrap_integrator.ps1 -Profile algotrading -RunChecklist -RunQuality`
