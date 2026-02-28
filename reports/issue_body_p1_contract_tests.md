## Тезис
Базовые smoke/контракты уже есть, и `run --json --json-strict` покрыт тестами. Источник: [test_smoke.py](file:///C:/integrator/tests/test_smoke.py), [test_projects.py](file:///C:/integrator/tests/test_projects.py#L657-L711).

## Антитезис (факты)
- **Проверено:** табличный контракт `agents status` с `--explain/--fix-hints` покрыт слабо. Источник: [cli_cmd_agents.py](file:///C:/integrator/cli_cmd_agents.py#L71-L108).
- **Проверено:** контракт `remotes` (only-github, SSH/HTTPS, exit-code семантика) покрыт недостаточно. Источник: [cli_cmd_git.py](file:///C:/integrator/cli_cmd_git.py#L67-L93).
- **Проверено:** `localai assistant --json` частично реализован, отсутствует тест на отсутствие утечек `--auth-token` в вывод. Источник: [cli_cmd_localai.py](file:///C:/integrator/cli_cmd_localai.py#L23-L73), [test_localai_cli.py](file:///C:/integrator/tests/test_localai_cli.py).
- **Проверено:** контракт roots/env (приоритет INTEGRATOR_ROOTS/TAST_ROOTS, разбор `;`) требует усиления тестами. Источник: [cli_env.py](file:///C:/integrator/cli_env.py#L50-L175).

## Синтез (задачи)
- [ ] **P1** Добавить контрактные тесты `agents status` для табличного режима: базовый, `--explain`, `--fix-hints`, совместно, `--only-problems`.
- [ ] **P1** Добавить контрактные тесты `remotes`: SSH/HTTPS, `.git`, пустой remote, `--only-github`, exit-code семантика.
- [ ] **P1** Добавить тесты `run` для табличного режима и ошибок с `--continue-on-error`.
- [ ] **P1** Зафиксировать контракт `localai assistant --json` и добавить тест на отсутствие утечки `--auth-token` в stdout/stderr.
- [ ] **P1** Добавить тесты на контракт env-roots (split `;`, trimming, приоритет, пустые сегменты).

## Acceptance criteria
- `python -m unittest discover -s tests -p "test*.py"` проходит.
- Покрытие критичных CLI-модулей повышено и регрессии контрактов ловятся тестами.

## Rollback
- `git restore --source=HEAD -- tests/ cli_cmd_agents.py cli_cmd_git.py cli_cmd_run.py cli_cmd_localai.py cli_env.py` для отмены правок.
