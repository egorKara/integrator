# Issue #28 execution report (2026-03-06)

## Scope
- Issue: `#28`
- Запрос: определить готовые вехи, приоритизировать, выполнить приоритетную веху, работать крупными блоками.

## Фактическое состояние вех
- Top-6 board (`P12..P17`) закрыт полностью: `state=completed` во всех пунктах.
- Крупные блоки, выполненные в рамках приоритетного цикла:
  - `P15`: калибровка профилей `research/coding/ops`.
  - `P16`: reference perf baseline + CI drift-check `reference -> current`.
  - `P17`: EPIC phase-1 kickoff с измеримыми SLI и rollback-контуром.

## Приоритизация после закрытия Top-6
1. `PROC-1` — Blocker: branch protection + required checks + 2 approvals.
2. `P1-4` — Major: PR/merge gate-контур (зависит от branch protection полномочий).
3. `DOC-1` — Major: документирование и порядок отката.

## Исполнение приоритетной вехи и результат
- Запущено исполнение `PROC-1` через `tools/apply_branch_protection.py`.
- Получен блокер внешней среды: GitHub API возвращает `403 Resource not accessible by personal access token` для branch protection endpoints.
- Артефакт фиксации: `reports/branch_protection_apply_20260306_225039.json`.

## Выполнен следующий исполнимый приоритет
- Закрыт `DOC-1` (документация и порядок отката):
  - `README.md` — добавлены точные требования к токену для branch protection.
  - `docs/CODE_REVIEW.md` — добавлена матрица требуемых прав токена и порядок размещения токена.
  - `reports/proc1_token_scope_diagnostic_2026-03-06.md` — диагностический артефакт по текущему токену.
- Актуализация execution-плана:
  - `P1-4` → `blocked` (зависит от `PROC-1`).
  - `DOC-1` → `done`.

## Синхронизация планов и дрейфа статусов
- `recommendations_execution_plan_2026-02-20.json`:
  - `PROC-1` переведён в `blocked` с явным описанием блокера.
- `recommendations_followup_plan_2026-02-20.md`:
  - `P0-PROC-1` → `Blocked (token scope)`.
  - `P2-CLI-1` → `Done (B7)`.
  - `P2-QUAL-2` → `Done (B4)`.
  - `P2-ARCH-1` → `Done (B10/P17)`.

## Следующий исполнимый внутренний приоритет (без внешних прав)
- Выполнен рефактор `algotrading` CLI по снижению дублирования:
  - `cli_cmd_algotrading.py`: добавлены `_merge_inline_env` и `_build_runtime_env`, унифицирована сборка env для `run`, `optimize-lessons`, `media-db-migrate`.
- Добавлены регрессионные тесты env/argv-контракта:
  - `tests/test_algotrading_cli.py` — покрыты precedence `config < env-file < --env` и флаги из config для optimize/migrate.
- Верификация:
  - `python -m unittest tests.test_algotrading_cli tests.test_execution_plan_consistency tests.test_ci_perf_drift_contract tests.test_p17_phase1_gate` → pass.
  - `python -m ruff check cli_cmd_algotrading.py tests/test_algotrading_cli.py` → pass.
  - `python -m mypy cli_cmd_algotrading.py tests/test_algotrading_cli.py` → pass.
- Очередь синхронизирована: `reports/telegram_github_worker_queue.jsonl` (`#27/#28` переведены в `done`).

## Next action
- Разблокировать `PROC-1` через token с правами admin к branch protection API.
- После разблокировки сразу повторить `tools/apply_branch_protection.py` и закрыть `P1-4`.

## Re-check после усиления токена
- Проверка проведена повторно:
  - `reports/branch_protection_apply_20260306_231532.json`
  - `reports/branch_protection_apply_20260306_231842.json`
- Итог: блокер уточнён — это не scope токена, а ограничение GitHub тарифа/типа репозитория (`403 Upgrade to GitHub Pro or make this repository public`).
- Уточнение в коде диагностики:
  - `github_api.py`: добавлена классификация `feature_unavailable_plan` для такого ответа API.
  - `tests/test_github_api.py`: добавлен тест классификации 403 plan-limit.

## Продолжение по внутренним приоритетам (без внешних зависимостей)
- Выполнена декомпозиция runtime-контура `algotrading`:
  - `cli_cmd_algotrading.py`: добавлен общий исполнитель `_execute_algotrading_script`, который унифицирует `python lookup`, запуск скрипта, payload/json-вывод и табличный вывод.
  - `run`, `optimize-lessons`, `media-db-migrate` переведены на общий исполнитель без изменения CLI-контрактов.
- Добавлены регрессионные тесты:
  - `tests/test_algotrading_cli.py`: негативные ветки `--base is required` и `python not found`.
- Верификация:
  - `python -m unittest tests.test_algotrading_cli tests.test_github_api tests.test_execution_plan_consistency` → pass.
  - `python -m ruff check cli_cmd_algotrading.py tests/test_algotrading_cli.py` → pass.
  - `python -m mypy cli_cmd_algotrading.py tests/test_algotrading_cli.py` → pass.
  - `python -m coverage run -m unittest tests.test_algotrading_cli` + `python -m coverage report -m cli_cmd_algotrading.py` → `78%` для `cli_cmd_algotrading.py`.

## Следующий внутренний приоритетный блок
- Поднят coverage `cli_cmd_obsidian.py` целевыми тестами на непокрытые ветки:
  - `doctor` ветка `status=error`.
  - `attachments delete` ветки `bad report_json` и `copy failure`.
  - `eval` ветка runtime-error при `--enable-eval`.
- Файлы:
  - `tests/test_cli_cmd_obsidian_module.py` — добавлены новые тесты error-path.
  - `AGENTS.md` — обновлён статус техдолга (для `cli_cmd_obsidian.py` зафиксировано 94%).
- Верификация:
  - `python -m unittest tests.test_cli_cmd_obsidian_module tests.test_obsidian_cli tests.test_execution_plan_consistency` → pass.
  - `python -m ruff check tests/test_cli_cmd_obsidian_module.py cli_cmd_obsidian.py` → pass.
  - `python -m mypy tests/test_cli_cmd_obsidian_module.py cli_cmd_obsidian.py` → pass.
  - `python -m coverage run -m unittest tests.test_cli_cmd_obsidian_module tests.test_obsidian_cli` + `python -m coverage report -m cli_cmd_obsidian.py` → `94%`.

## Решение по внешнему блокеру
- GitHub Pro зафиксирован как отложенный (бюджетный приоритет).
- Подготовлен анализ сценария public-репозитория:
  - `reports/public_repo_tradeoff_2026-03-06.md` (изменения, риски, выгоды, меры снижения рисков).

## Следующий внутренний приоритетный блок (cli_cmd_localai)
- Поднят coverage `cli_cmd_localai.py` целевыми тестами на непокрытые ветки:
  - `memory-recent` и `memory-retrieve` (параметры, фильтры, JSON records).
  - `memory-feedback` успешная ветка в tab-режиме.
  - `memory-write` ветки `content_file missing` и mixed-status в JSON-режиме.
  - `gateway_json` (загрузка маршрутов и прокидывание routes в клиент).
  - проверки `cwd missing` и `recipe target missing`.
- Файл:
  - `tests/test_cli_cmd_localai_module.py` — добавлены целевые тесты error/success-path.
- Верификация:
  - `python -m unittest tests.test_cli_cmd_localai_module tests.test_localai_cli tests.test_execution_plan_consistency` → pass.
  - `python -m ruff check tests/test_cli_cmd_localai_module.py cli_cmd_localai.py` → pass.
  - `python -m mypy tests/test_cli_cmd_localai_module.py cli_cmd_localai.py` → pass.
  - `python -m coverage run -m unittest tests.test_cli_cmd_localai_module tests.test_localai_cli` + `python -m coverage report -m cli_cmd_localai.py` → `90%`.
- Актуализация техдолга:
  - `AGENTS.md`: из low-coverage списка убран `cli_cmd_localai.py`; фокус остался на `tslab_offline_csv.py`.

## Следующий внутренний приоритетный блок (tslab_offline_csv)
- Поднят coverage `tslab_offline_csv.py` до 99% целевыми тестами:
  - ошибки структуры ответа MOEX (`missing columns`, `invalid numeric`).
  - проброс сетевой ошибки (`urlopen` exception).
  - timezone-конверсия в `write_tslab_offline_csv`.
  - ветка `--out-finam` с пробелами (пропуск экспорта Finam).
  - ошибки CLI-парсинга `argparse` (missing required args, invalid interval).
- Файл:
  - `tests/test_tslab_offline_csv.py` — добавлены целевые error-path и edge-case тесты.
- Верификация:
  - `python -m unittest tests.test_tslab_offline_csv tests.test_execution_plan_consistency` → pass.
  - `python -m ruff check tests/test_tslab_offline_csv.py tslab_offline_csv.py` → pass.
  - `python -m mypy tests/test_tslab_offline_csv.py tslab_offline_csv.py` → pass.
  - `python -m coverage run -m unittest tests.test_tslab_offline_csv` + `python -m coverage report -m tslab_offline_csv.py` → `99%`.
- Актуализация техдолга:
  - `AGENTS.md`: low-coverage список закрыт, покрытие целевых модулей зафиксировано.

## Следующий внутренний приоритетный блок (декомпозиция cli.py)
- Выполнена декомпозиция без изменения внешнего поведения:
  - добавлен новый модуль `cli_parser_core.py` с разбиением сборки argparse по подсистемам (`projects/agents/localai/chains/registry/git/session` и базовые команды).
  - в `cli.py` сохранён публичный фасад (`run`, re-export patch-point’ов), а `_build_parser` стал thin-wrapper над `build_parser(...)`.
- Верификация совместимости:
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`350` tests).
  - `python -m unittest tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_cmd_misc_module` → pass.
  - `python -m ruff check cli.py cli_parser_core.py tests/test_cli_contracts_golden.py` → pass.
  - `python -m mypy cli.py cli_parser_core.py` → pass.
  - Примечание по репозиторию: `python -m mypy .` продолжает падать на уже существующих ошибках в `tools/check_p17_phase1_gate.py` и `tools/check_execution_plan_consistency.py` (вне области этого блока).
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирован статус декомпозиции `cli.py` и следующий шаг.

## Следующий внутренний приоритетный блок (декомпозиция фасада/роутинга cli.py)
- Выполнена дополнительная декомпозиция без изменения контрактов:
  - добавлен `cli_runtime.py` (слой запуска/роутинга: `default_prog`, `build_cli_parser`, `run_cli`);
  - `cli.py` переведён на thin-facade поверх runtime-слоя при сохранении re-export patch-point’ов;
  - добавлены модульные тесты `tests/test_cli_runtime_module.py`.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_runtime_module tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli.py cli_runtime.py cli_parser_core.py tests/test_cli_runtime_module.py tests/test_cli_contracts_golden.py` → pass.
  - `python -m mypy cli.py cli_runtime.py cli_parser_core.py tests/test_cli_runtime_module.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирован двухслойный статус (`cli_parser_core.py` + `cli_runtime.py` + фасад `cli.py`).

## Следующий внутренний приоритетный блок (доменная декомпозиция cli_parser_core.py)
- Выполнена доменная декомпозиция parser-слоя без изменения контрактов:
  - добавлены `cli_parser_projects.py`, `cli_parser_agents.py`, `cli_parser_localai.py`;
  - `cli_parser_core.py` переведён на orchestration-вызовы доменных модулей;
  - внешние команды и ключи аргументов сохранены без изменений.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_runtime_module tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli_parser_core.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_runtime.py cli.py` → pass.
  - `python -m mypy cli_parser_core.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_runtime.py cli.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирована новая структура CLI-слоя с доменными parser-подмодулями.

## Следующий внутренний приоритетный блок (дальнейшая доменная декомпозиция parser-слоя)
- Выполнено выделение оставшихся parser-блоков из `cli_parser_core.py`:
  - добавлены `cli_parser_chains.py`, `cli_parser_registry.py`, `cli_parser_git.py`, `cli_parser_session.py`;
  - `cli_parser_core.py` переведён на вызовы `add_chains_parsers/add_registry_parsers/add_git_parsers/add_session_parsers`;
  - внешние CLI-контракты, команды и аргументы сохранены без изменений.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_runtime_module tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli_parser_core.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_parser_chains.py cli_parser_registry.py cli_parser_git.py cli_parser_session.py cli_runtime.py cli.py` → pass.
  - `python -m mypy cli_parser_core.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_parser_chains.py cli_parser_registry.py cli_parser_git.py cli_parser_session.py cli_runtime.py cli.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирована расширенная модульная структура parser-слоя.

## Следующий внутренний приоритетный блок (вынос общих parser-блоков)
- Выполнен вынос оставшихся общих блоков из `cli_parser_core.py`:
  - добавлены `cli_parser_health.py` (`doctor/diagnostics/preflight`);
  - добавлены `cli_parser_batch.py` (`status/remotes/run/report`);
  - добавлены `cli_parser_tools.py` (`rg/exec/hygiene`);
  - `cli_parser_core.py` оставлен orchestration-слоем и подключает новые `add_*_parsers`.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_runtime_module tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli_parser_core.py cli_parser_health.py cli_parser_batch.py cli_parser_tools.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_parser_chains.py cli_parser_registry.py cli_parser_git.py cli_parser_session.py cli_runtime.py cli.py` → pass.
  - `python -m mypy cli_parser_core.py cli_parser_health.py cli_parser_batch.py cli_parser_tools.py cli_parser_projects.py cli_parser_agents.py cli_parser_localai.py cli_parser_chains.py cli_parser_registry.py cli_parser_git.py cli_parser_session.py cli_runtime.py cli.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксированы общие parser-модули (`health/batch/tools`) в составе CLI-архитектуры.

## Следующий внутренний приоритетный блок (точечная чистка orchestration-слоя)
- Выполнена локальная чистка оркестратора без изменения поведения:
  - в `cli_parser_core.py` введены групповые регистраторы `_register_primary_parsers` и `_register_extension_parsers`;
  - `build_parser(...)` упрощён до последовательного вызова этих регистраторов;
  - состав и порядок подключаемых parser-модулей сохранены.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_runtime_module tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli_parser_core.py cli_parser_health.py cli_parser_batch.py cli_parser_tools.py` → pass.
  - `python -m mypy cli_parser_core.py cli_parser_health.py cli_parser_batch.py cli_parser_tools.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: отмечено завершение локальной чистки orchestration-слоя.

## Следующий внутренний приоритетный блок (нулевой cleanup фасада и runtime)
- Выполнена точечная структурная чистка без изменения контрактов:
  - `cli_runtime.py`: выделены внутренние helpers `_argv_list/_argv_prog/_argv_args` для читаемости пайплайна `run_cli`;
  - `cli.py`: добавлен явный thin-facade делегатор `_run_cli`, `run(...)` делегирует через него, `_build_parser` переведён на явный keyword-стиль;
  - внешний API и patch-point’ы сохранены.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_runtime_module tests.test_cli_contracts_golden tests.test_preflight tests.test_localai_cli tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check cli.py cli_runtime.py cli_parser_core.py` → pass.
  - `python -m mypy cli.py cli_runtime.py cli_parser_core.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирована точечная чистка фасада и runtime без изменения поведения.

## Следующий внутренний приоритетный блок (микроклининг CLI контракт-тестов)
- Выполнен нулевой по риску рефакторинг читаемости тестов без изменения проверяемого поведения:
  - `tests/test_cli_contracts_golden.py`: добавлены локальные helper-методы подготовки проекта и проверки JSON-ключей, убрано дублирование фикстур/ассертов;
  - `tests/test_cli_runtime_module.py`: добавлен helper-конструктор parser mock для повышения читаемости тест-кейса dispatch.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_contracts_golden tests.test_cli_runtime_module tests.test_preflight tests.test_localai_cli tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`352` tests).
  - `python -m ruff check tests/test_cli_contracts_golden.py tests/test_cli_runtime_module.py cli.py cli_runtime.py cli_parser_core.py` → pass.
  - `python -m mypy tests/test_cli_contracts_golden.py tests/test_cli_runtime_module.py cli.py cli_runtime.py cli_parser_core.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксирован микроклининг CLI контракт-тестов без изменения поведения.

## Следующий внутренний приоритетный блок (P0 secret hygiene в quality summary)
- Выполнена проверка открытых/незавершённых задач по docs/reports и выбран исполнимый P0-блок:
  - подтверждено отсутствие conflict markers в текущем репозитории integrator (историческая задача уже закрыта переносом подпроекта);
  - реализован `no_secrets` gate в `quality summary` через `guardrails.py --strict --json --scan-tracked --scan-reports`.
- Изменения реализации:
  - `cli_quality.py`: добавлен `_no_secrets_gate(...)`, включён в `gates` и табличный вывод `quality summary`;
  - `tests/test_cli_quality_module.py`: добавлен тест на включение `no_secrets` gate без изменения существующего контрактного поведения.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_quality_module tests.test_cli_contracts_golden tests.test_cli_runtime_module tests.test_preflight tests.test_localai_cli tests.test_cli_cmd_misc_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`353` tests).
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксировано добавление `no_secrets` gate в `quality summary`.

## Следующий внутренний приоритетный блок (подготовка к разблокировке PROC-1/P1-4)
- Выполнен исполнимый шаг для внешнего блокера branch protection:
  - добавлена команда `integrator quality public-readiness` с JSON-артефактом готовности к переводу репозитория в public;
  - в проверку включены `no_secrets` (оценка только `secret_scan-*` из guardrails) и `tracked_safety` (контроль `vault/*` и `.env*` в tracked-файлах, кроме `.env.example`).
- Изменения реализации:
  - `cli_quality.py`: добавлены `_git_tracked_files(...)`, `_tracked_safety_gate(...)`, `_cmd_quality_public_readiness(...)`; расширен parser `quality` новым subcommand `public-readiness`; уточнён `_no_secrets_gate(...)` для secret-only семантики.
  - `tests/test_cli_quality_module.py`: добавлены тесты на `tracked_safety` и `public-readiness` report.
- Верификация совместимости:
  - `python -m unittest tests.test_cli_quality_module` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`355` tests).
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m integrator quality public-readiness --json` → pass (`ok=true`, артефакт: `reports/public_repo_readiness_20260307_105614.json`).
- Актуализация техдолга:
  - `AGENTS.md`: уточнена семантика `no_secrets` gate и зафиксирован readiness-контур для public-перехода.

## Финальный операционный шаг (runbook перед внешним действием в GitHub settings)
- Добавлен короткий runbook `public-readiness -> apply branch protection`:
  - `docs/CODE_REVIEW.md`: секция с 4 шагами (readiness, внешний public-переход, check-only, apply).
  - `README.md`: зеркальный практический блок команд для оператора.
- Верификация runbook-команд:
  - `python -m integrator quality public-readiness --json` → pass (`ok=true`, артефакт: `reports/public_repo_readiness_20260307_110330.json`).
  - `python tools/apply_branch_protection.py --check-only` → выполнено, записан артефакт проверки `reports/branch_protection_apply_20260307_110330.json`.
- Общая валидация после документирования:
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`355` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.
- Актуализация техдолга:
  - `AGENTS.md`: зафиксировано добавление runbook-блока в README/CODE_REVIEW.

## Продолжение после runbook (точная диагностика блокера PROC-1)
- Выполнен реальный `apply`-прогон branch protection после оформления runbook.
- Обнаружено, что при private-репозитории API-ответы частично маскируются (`404`) и усложняют triage.
- Улучшение без смены внешнего контракта:
  - `tools/apply_branch_protection.py`: добавлена ранняя precondition-проверка `visibility=private` с явным статусом `feature_unavailable_plan`; при таком состоянии пишется отчёт и выполнение завершается без бесполезных PATCH/POST к protection endpoints.
  - `tests/test_apply_branch_protection.py`: добавлены тесты для веток `private precondition blocker` и `--check-only` поведения.
- Верификация:
  - `python -m unittest tests.test_apply_branch_protection tests.test_cli_quality_module` → pass.
  - `python -m ruff check tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python tools/apply_branch_protection.py` → pass по исполнению скрипта, артефакт: `reports/branch_protection_apply_20260307_112901.json` (явный `precondition_visibility.feature_unavailable_plan`).
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`357` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Продолжение после precondition-диагностики (visibility gate в readiness)
- Выявлен operational gap: `quality public-readiness` не включал явную проверку `repo visibility`, хотя это прямой внешний предикат для разблокировки `PROC-1`.
- Улучшение без смены базовых CLI-контрактов:
  - `cli_quality.py`: добавлен `repo_visibility` gate в `quality public-readiness` (через GitHub API `GET /repos/{owner}/{repo}`), добавлен параметр `--repo` с fallback на `GITHUB_REPOSITORY`.
  - `tests/test_cli_quality_module.py`: обновлён тест `public-readiness` и добавлен тест private-visibility ветки.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m integrator quality public-readiness --json` → ожидаемо `ok=false` при private visibility; артефакт: `reports/public_repo_readiness_20260307_114407.json` (явный `gates.repo_visibility`).
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`358` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Проверка после ручного апдейта GitHub Settings
- Выполнена повторная верификация состояния репозитория и protection-контура после сообщения оператора о включении настроек.
- Подтверждено по API:
  - `default_branch=main`;
  - `allow_merge_commit=true`, `allow_squash_merge=true`, `allow_rebase_merge=true`;
  - `allow_auto_merge=false`;
  - `visibility=private` (ключевой блокер для `PROC-1` остаётся).
- Верификация:
  - `python -m integrator quality public-readiness --json` → `ok=false`, артефакт: `reports/public_repo_readiness_20260307_121538.json` / `reports/public_repo_readiness_20260307_121625.json`.
  - `python tools/apply_branch_protection.py` → артефакт: `reports/branch_protection_apply_20260307_121625.json`, статус `precondition_visibility.feature_unavailable_plan`.
  - `python tools/apply_branch_protection.py --check-only` → артефакт: `reports/branch_protection_apply_20260307_121558.json`.
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.
- Вывод:
  - Внутренний контур и диагностика корректны, но внешний шаг `Change repository visibility -> public` ещё не завершён; до этого `PROC-1/P1-4` остаются `blocked`.

## Повторная проверка после подтверждения оператора «готово»
- Повторный preflight и API-проверка подтвердили, что внешний шаг visibility завершён:
  - `visibility=public`;
  - `default_branch=main`;
  - merge-режимы (`merge/squash/rebase`) включены, `auto-merge` выключен.
- Верификация:
  - `python -m integrator quality public-readiness --json` → `ok=true`, артефакт: `reports/public_repo_readiness_20260307_122206.json`.
  - `python tools/apply_branch_protection.py` → артефакт: `reports/branch_protection_apply_20260307_122206.json`, однако sub-checks branch protection возвращают `404` (`required_status_checks`, `required_pull_request_reviews`, `enforce_admins`).
  - `python tools/apply_branch_protection.py --check-only` → артефакт: `reports/branch_protection_apply_20260307_122208.json`.
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.
- Вывод:
  - Переход в `public` подтверждён и readiness-блокер снят.
  - Остался отдельный технический вопрос применения branch protection через текущий API-поток (404 на protection sub-endpoints), требует корректировки вызовов/порядка в `tools/apply_branch_protection.py`.

## Исправление apply_branch_protection (без 404 на текущем репозитории)
- Реализована смена прикладного потока:
  - `tools/apply_branch_protection.py` переведён с legacy branch-protection sub-endpoints на repository rulesets API (`/repos/{owner}/{repo}/rulesets`).
  - Скрипт теперь upsert-ит ruleset `integrator-main-protection` для `refs/heads/main` с правилами `pull_request` (2 approvals, code-owner review, dismiss stale reviews, thread resolution) и `required_linear_history`.
- Верификация:
  - `python tools/apply_branch_protection.py` → pass, артефакт: `reports/branch_protection_apply_20260307_124202.json` (`apply_ruleset.ok=true`, без 404 path).
  - `python -m unittest tests.test_apply_branch_protection` → pass.
  - `python -m ruff check tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`360` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.
- Примечание:
  - Для текущего режима rulesets API устраняет 404 legacy-пути; enforcement выполняется через ruleset `integrator-main-protection`.

## Усиление quality public-readiness: проверка ruleset
- В `quality public-readiness` добавлен новый gate `repo_ruleset`, который проверяет наличие ruleset `integrator-main-protection` и его `enforcement=active`.
- Технически:
  - Реализован `_repo_ruleset_gate(...)` в `cli_quality.py`;
  - Gate включён в payload `public_repo_readiness` и табличный вывод команды.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py` → pass.
  - `python -m integrator quality public-readiness --json` → `ok=true`, артефакт: `reports/public_repo_readiness_20260307_125158.json` (включает `gates.repo_ruleset.code=0`).
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`362` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Проверка ruleset по содержимому + required status checks
- Расширен `repo_ruleset` gate: теперь он валидирует policy-содержимое ruleset, а не только `enforcement=active`.
- Проверяемые инварианты:
  - `required_linear_history` включён;
  - `pull_request` содержит: `required_approving_review_count>=2`, `require_code_owner_review=true`, `dismiss_stale_reviews_on_push=true`, `required_review_thread_resolution=true`;
  - наличие `required_status_checks` со strict policy и контекстом `ci / test`.
- Попытка расширить сам ruleset на `required_status_checks` через rulesets API на текущем репозитории вернула `422` (невалидный rule shape), поэтому apply-поток оставлен стабильным, а несовпадение фиксируется gate-ом.
- Верификация:
  - `python -m unittest tests.test_apply_branch_protection tests.test_cli_quality_module` → pass.
  - `python -m ruff check tools/apply_branch_protection.py cli_quality.py tests/test_apply_branch_protection.py tests/test_cli_quality_module.py` → pass.
  - `python -m mypy tools/apply_branch_protection.py cli_quality.py tests/test_apply_branch_protection.py tests/test_cli_quality_module.py` → pass.
  - `python tools/apply_branch_protection.py` → pass, артефакт: `reports/branch_protection_apply_20260307_155359.json`.
  - `python -m integrator quality public-readiness --json` → `ok=false`, артефакт: `reports/public_repo_readiness_20260307_155403.json` (`repo_ruleset.error_kind=ruleset_policy_mismatch`, отсутствуют required status checks).
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`363` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Auto-remediation mode (plan-only) для ruleset_policy_mismatch
- В `quality public-readiness` добавлен безопасный режим планирования:
  - `--auto-remediation-plan` включает генерацию remediation-плана;
  - `--write-remediation-plan <path>` задаёт путь артефакта плана.
- При `repo_ruleset.error_kind=ruleset_policy_mismatch` формируются:
  - точный `policy_diff` (path/current/desired/action),
  - отдельный JSON-план применения без авто-мутаций (`blind_put=false`, `requires_manual_review=true`).
- Артефакты последней верификации:
  - readiness: `reports/public_repo_readiness_20260307_160200.json`;
  - remediation plan: `reports/ruleset_remediation_plan_20260307_160200.json`.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m integrator quality public-readiness --json --auto-remediation-plan` → `ok=false` (ожидаемо по mismatch), remediation plan создан.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`364` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Candidate payloads + probe dry-run (управляемый мост diff -> safe apply)
- В remediation-план добавлены `candidate_payloads` с несколькими вариантами shape для required status checks:
  - `candidate_rule_strict`,
  - `candidate_rule_simple`,
  - `candidate_pull_request_nested`.
- Добавлен probe dry-run без мутаций:
  - флаг `--probe-ruleset-payloads` запускает локальную schema/риск-проверку candidates;
  - в план пишется блок `probe` с ранжированием и `recommended_candidate_id`.
- Артефакты:
  - readiness: `reports/public_repo_readiness_20260307_161220.json`;
  - remediation plan: `reports/ruleset_remediation_plan_20260307_161220.json`.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m integrator quality public-readiness --json --auto-remediation-plan --probe-ruleset-payloads` → `ok=false` (ожидаемо), remediation/probe артефакты сформированы.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`364` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Manual apply approved candidate + post-check readiness
- Добавлена отдельная команда: `quality apply-approved-candidate`.
- Контракт безопасности:
  - обязательный `--confirm APPLY` (иначе команда завершается с кодом `2`);
  - применяется только выбранный `--candidate-id` из указанного `--plan`;
  - после apply автоматически формируется post-check readiness отчёт.
- Поведение на текущем репозитории:
  - запуск `candidate_rule_simple` выполнил безопасный pipeline, но apply вернул `422` от GitHub API (shape still unsupported), post-check зафиксировал `ok=false`.
- Артефакты:
  - apply report: `reports/apply_approved_candidate_20260307_161825.json`;
  - post-check readiness: `reports/public_repo_readiness_post_apply_20260307_161825.json`;
  - readiness/remediation перед apply: `reports/public_repo_readiness_20260307_161823.json`, `reports/ruleset_remediation_plan_20260307_161823.json`.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m integrator quality apply-approved-candidate --repo egorKara/integrator --plan reports/ruleset_remediation_plan_20260307_161220.json --candidate-id candidate_rule_simple --confirm APPLY --json` → выполнен, `apply_result.status=422`, post-check сформирован.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`366` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Probe-on-remote для candidate payloads (временный безопасный контур)
- В `quality public-readiness` добавлен опциональный режим `--probe-on-remote` (только вместе с `--probe-ruleset-payloads`).
- Режим выполняет remote-проверку shape кандидатов через GitHub API в временном контуре:
  - создаёт временный disabled ruleset на probe-ref `refs/heads/__integrator_probe__*`,
  - при успехе удаляет его (`temporary_create_delete`),
  - пишет для каждого кандидата `probe_status`, `probe_error_kind`, `cleanup_ok`.
- Если нет ни одного поддержанного кандидата, `recommended_candidate_id` остаётся пустым.
- Артефакты:
  - readiness: `reports/public_repo_readiness_20260307_162519.json`;
  - remediation plan с remote probe: `reports/ruleset_remediation_plan_20260307_162519.json`.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m integrator quality public-readiness --json --auto-remediation-plan --probe-ruleset-payloads --probe-on-remote` → `ok=false` (ожидаемо), remote-probe артефакты сформированы.
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`368` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.

## Shape-adapter + compatible_payload + api_shape_compatibility gate
- В remote probe добавлен shape-adapter слой с автоматическим перебором адаптеров:
  - `identity_pruned` (pruning unknown),
  - `checks_as_strings` (альтернативный формат required checks),
  - `status_checks_alt_key` (альтернативный ключ checks),
  - `minimal_pull_request` (минимизация pull_request полей).
- В remediation-plan теперь пишется:
  - `compatible_payload` при найденном поддержанном shape;
  - `adapter_failures` таблица отказов по адаптерам, если совместимый shape не найден.
- `apply-approved-candidate` обновлён:
  - `--use-compatible-payload` применяет только `compatible_payload`;
  - при его отсутствии — fail-fast с понятной ошибкой `compatible_payload_missing`.
- В `public-readiness` добавлен отдельный gate `api_shape_compatibility`:
  - `supported/unsupported` отражает API-совместимость shape независимо от policy mismatch.
- Актуальный runbook:
  - `mismatch -> probe-on-remote(+adapter) -> compatible_payload -> manual apply --confirm APPLY -> post-check`.
- Артефакты:
  - readiness: `reports/public_repo_readiness_20260307_164940.json`;
  - remediation plan: `reports/ruleset_remediation_plan_20260307_164940.json`.
- Верификация:
  - `python -m unittest tests.test_cli_quality_module tests.test_apply_branch_protection` → pass.
  - `python -m ruff check cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m mypy cli_quality.py tests/test_cli_quality_module.py tools/apply_branch_protection.py tests/test_apply_branch_protection.py` → pass.
  - `python -m integrator quality public-readiness --json --auto-remediation-plan --probe-ruleset-payloads --probe-on-remote` → `ok=false`, `api_shape_compatibility=shape_unsupported` (ожидаемо).
  - `python -m integrator quality apply-approved-candidate --repo egorKara/integrator --plan reports/ruleset_remediation_plan_20260307_162519.json --candidate-id candidate_rule_simple --use-compatible-payload --confirm APPLY --json` → fail-fast `compatible_payload_missing` (ожидаемо).
  - `python -m unittest discover -s tests -p "test*.py"` → pass (`370` tests).
  - `python -m tools.check_execution_plan_consistency --reports-dir reports --json` → pass.
