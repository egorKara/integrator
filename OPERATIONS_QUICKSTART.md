# Operations Quickstart

## Быстрый старт
- `python -m integrator doctor`
- `python -m integrator diagnostics --only-problems`
- `python -m integrator projects list --max-depth 4`
- `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`
- `python -m integrator registry list`
- `python -m integrator chains list`

## Артефакты в репозитории
- `reports/`: отчёты качества, security, перф-бейзлайны и operator-логи (по необходимости).
- `.trae/memory/`: локальные рабочие файлы сессий; в VCS обязателен только `project_memory.xml`.

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
- `python -m integrator run build --dry-run`

## LocalAI assistant
- `python -m integrator localai list --root C:\LocalAI --max-depth 3`
- `python -m integrator localai assistant rag --cwd C:\LocalAI\assistant`
- `python -m integrator localai assistant rag --cwd C:\LocalAI\assistant --daemon`
- `python -m integrator localai assistant reindex --cwd C:\LocalAI\assistant`

## Git bootstrap ignore
- `python -m integrator git bootstrap-ignore --dry-run`

## Quality-First Self-Tuning
- `python guardrails.py --strict --json`
- `python ops_checklist.py --json`
- `.\scripts\bootstrap_integrator.ps1 -Profile full -InstallPreCommit -RunChecklist -RunQuality`
- `.\scripts\bootstrap_integrator.ps1 -Profile algotrading -RunChecklist -RunQuality`
