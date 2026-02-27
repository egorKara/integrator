# integrator

CLI-интегратор для массовых операций по локальным проектам.

## Документация (вход)
- Индекс документации: `docs/DOCS_INDEX.md`

## Установка
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Операторские зависимости
По умолчанию `requirements.txt` содержит только инструменты качества (ruff/mypy/coverage).

Для расширенного операторского окружения (LocalAI/инструменты) используйте:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.operator.txt
```

## Быстрая инициализация dev-среды
```powershell
.\tools\dev_setup.ps1
```

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

## Operations quickstart
Сводка команд для операторских сценариев: `OPERATIONS_QUICKSTART.md`.

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

## Переменные окружения
Пример находится в `.env.example`.

## Roots
- По умолчанию: `C:\vault\Projects`, `C:\LocalAI` (если доступны)
- Переопределение: `INTEGRATOR_ROOTS="C:\A;C:\B"` (поддерживается `TAST_ROOTS`)
- Дополнительно: `VAULT_ROOT`, `LOCALAI_ROOT`, `LOCALAI_ASSISTANT_ROOT`

## Тесты
```powershell
python -m unittest discover -s tests -p "test*.py"
```

## Typecheck
```powershell
python -m mypy .
```

## Coverage
```powershell
python -m coverage run -m unittest discover -s tests -p "test*.py"
python -m coverage report -m
python -m coverage xml -o reports\coverage.xml
```

## CI
- GitHub Actions: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Gates: ruff, mypy, unittest, coverage report `--fail-under=80`
- Security: gitleaks + pip-audit, отчёты публикуются как artifacts (`reports/*.json`)
- Required check: `ci / test` (удобно для Branch Protection)

## Quality summary
```powershell
python -m integrator quality summary --json
python -m integrator quality summary --json --write-report reports\quality_summary.json
```

## Workflow: preflight → memory-write → report
```powershell
python -m integrator workflow preflight-memory-report --content-file .\note.txt --summary "ops run"
```

## LM Studio sidecar
Sidecar-анализ артефактов `reports/` через LM Studio: `docs/LLM_SIDECAR.md`.

## Code review
- Политика: `docs/CODE_REVIEW.md`
- Шаблон PR: `.github/pull_request_template.md`

## Восстановление данных
Файлы:
- `C:\LocalAI\cache\agent_memory.db`
- `C:\LocalAI\logs\agent_metrics.jsonl`
- `C:\LocalAI\logs\rag_metrics.jsonl`

Порядок:
```powershell
Copy-Item <backup_path>\agent_memory.db C:\LocalAI\cache\agent_memory.db -Force
Copy-Item <backup_path>\agent_metrics.jsonl C:\LocalAI\logs\agent_metrics.jsonl -Force
Copy-Item <backup_path>\rag_metrics.jsonl C:\LocalAI\logs\rag_metrics.jsonl -Force
```

## Документация изменений
- `docs/TECHNICAL_CHANGELOG_2026-02-20.md`
- `CHANGELOG.md`
- `reports/quality_report_2026-02-20.md`
- `reports/audit_conclusion_2026-02-20.md`
- `reports/recommendations_execution_note_2026-02-20.md`

## Quality-First Bootstrap
```powershell
# full quality-first bootstrap (по умолчанию)
.\scripts\bootstrap_integrator.ps1 -InstallPreCommit -RunChecklist -RunQuality

# профиль для AlgoTrading
.\scripts\bootstrap_integrator.ps1 -Profile algotrading -InstallPreCommit -RunChecklist -RunQuality
```

## Guardrails
```powershell
python guardrails.py --strict --json
python guardrails.py --strict --json --write-report reports\guardrails_manual.json
```

## Ops Checklist
```powershell
python ops_checklist.py --json
python ops_checklist.py --json --quick
```
