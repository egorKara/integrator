# integrator

CLI-интегратор для массовых операций по локальным проектам.

## Быстрый старт
```powershell
python -m integrator doctor
python -m integrator projects list --max-depth 2
python -m integrator agents list --max-depth 4
python -m integrator status --only-dirty --jobs 16
python -m integrator report --json --max-depth 2
python -m integrator registry list
python -m integrator chains list
```

## Ограничение выборки
```powershell
python -m integrator status --project localai --limit 50
python -m integrator remotes --only-github --project vpn
python -m integrator projects info --json --project fedora
```

## Пайплайны
```powershell
python -m integrator run lint --dry-run --project assistant
python -m integrator run test --continue-on-error --max-depth 2
python -m integrator run test --json --json-strict --project assistant
python -m integrator agents status --json --roots C:\LocalAI --max-depth 4
python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4
python -m integrator localai assistant rag --cwd C:\LocalAI\assistant --daemon
```

- Для машинного парсинга используйте `--json --json-strict`: в `stdout` останется только JSONL, вывод дочерних команд уйдёт в `stderr`.

## Roots
- По умолчанию: `C:\vault\Projects`, `C:\LocalAI`
- Переопределение: `INTEGRATOR_ROOTS="C:\A;C:\B"` (поддерживается `TAST_ROOTS`)

## Тесты
```powershell
python -m unittest discover -s tests -p "test*.py"
```
