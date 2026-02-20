# Operations Quickstart

## Быстрый старт
- `python -m integrator doctor`
- `python -m integrator diagnostics --only-problems`
- `python -m integrator projects list --max-depth 4`
- `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`
- `python -m integrator registry list`
- `python -m integrator chains list`

## Статусы репозиториев
- `python -m integrator status --only-dirty`
- `python -m integrator remotes --only-github`
- `python -m integrator report --json`

## Агенты
- `python -m integrator agents list --json --roots C:\LocalAI --max-depth 4`
- `python -m integrator agents status --json --only-problems --fix-hints --roots C:\LocalAI --max-depth 4`

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
