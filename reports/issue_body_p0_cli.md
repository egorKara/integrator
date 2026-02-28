## Тезис
Проект уже разделён на модули (scan/git_ops/run_ops/agents_ops/cli/utils), и основные команды имеют стабильные контракты вывода.

## Антитезис (факты)
- **Проверено:** `utils._load_global_gitignore()` вычисляет корень как `Path(__file__).resolve().parents[1]`, что на текущей структуре даёт `C:\` и ломает чтение `.trae/global_gitignore_localai`. Источник: [utils.py](file:///C:/integrator/utils.py#L47-L55) и наличие файла [.trae/global_gitignore_localai](file:///C:/integrator/.trae/global_gitignore_localai).
- **Проверено:** тест `git bootstrap-ignore` использует mock `_load_global_gitignore`, поэтому не ловит дефект чтения реального файла. Источник: [test_projects.py](file:///C:/integrator/tests/test_projects.py#L214-L241).
- **Проверено:** `WorkerError` не сериализуется в JSON для `status/remotes/report`, что ухудшает диагностику при `--json`. Источник: [cli_parallel.py](file:///C:/integrator/cli_parallel.py#L14-L24), [cli_cmd_git.py](file:///C:/integrator/cli_cmd_git.py#L25-L63).

## Синтез (задачи)
- [ ] **P0** Исправить вычисление repo root для `.trae/global_gitignore_localai` и добавить регрессионный тест, читающий реальный файл.
- [ ] **P0** Убрать mock в тесте `git bootstrap-ignore` и проверять фактическое наполнение игнора.
- [ ] **P1** Добавить поле `error` в JSON-строки `status/remotes/report` при `WorkerError`, покрыть тестом.

## Acceptance criteria
- `python -m unittest discover -s tests -p "test*.py"` проходит.
- `python -c "import utils; print(len(utils._load_global_gitignore()))"` печатает число больше 0.
- `python -m integrator git bootstrap-ignore --roots . --max-depth 1 --dry-run` завершаетcя с `exit_code=0`.
- При искусственной ошибке worker JSON-строка содержит поле `error` с текстом ошибки.

## Rollback
- `git restore --source=HEAD -- utils.py tests/test_projects.py` для отмены правок.
