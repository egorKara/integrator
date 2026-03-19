# Agents.md (for this project)

## Scope
- Project root: `C:\integrator`
- Core code: `*.py` в корне проекта
- Tests: `tests/`
- Project rules/memory/skills: `.trae/`

## Docs Entry
- Индекс документации: `docs/DOCS_INDEX.md`

## Assistant Rules
- Отвечать по-русски, если пользователь явно не просит иначе.
- Подход: Тезис -> Антитезис -> Синтез.
- Любое утверждение о работоспособности подтверждать командами/тестами/логами.
- Не выполнять разрушительные действия без явного запроса.
- Секреты не писать в код/логи/отчёты.
- Временные ограничения сессии (лимит токенов/времени) считать только текущим контекстом.
- Не фиксировать сессионные лимиты в постоянной документации, если пользователь не попросил явно.

## Trae 3.5.35 Workflow Note
- Markdown: использовать переключение Editor/Preview и фиксировать путь к отчётам.
- Команды агента не открывают терминал автоматически; детали смотреть через terminal card.
- После каждого запуска команд явно фиксировать статус/итог в ответе.

## Default Workflow
1. Сначала быстрый preflight.
2. Затем минимальные изменения с максимальной пользой.
3. После изменений обязательная валидация quality gates.
4. В конце краткий changelog с путями и фактами проверок.

## Preflight Commands
- `python -m integrator preflight --check-only --json`
- `python -m integrator doctor`
- `python -m integrator projects list --max-depth 4`
- `python -m integrator agents list --json --roots C:\LocalAI --max-depth 4`
- `python -m integrator agents status --json --only-problems --roots C:\LocalAI --max-depth 4`
- `python -m tools.check_skills_sync --json`

## Key CLI Contracts
- Табличный вывод по умолчанию.
- `--json`: JSON object per line.
- `run --json --json-strict`: в `stdout` только JSONL, вывод дочерних команд в `stderr`.
- `agents status --only-problems`: выводит только проблемные agent-проекты.

## Problem Semantics (`agents status`)
- Возможные источники проблем:
- `git_error`, `git_tool-missing`
- `gateway_base_missing`, `gateway_unreachable`, `gateway_routes_missing`
- `media_root_empty|missing`, `work_root_empty|missing`, `publish_root_empty|missing`

## Quality Gates
- `python -m tools.check_skills_sync --json`
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest discover -s tests -p "test*.py"`

## Active Technical Debt
- CLI-слой декомпозирован и локально очищен без смены контрактов: фасад `cli.py`, runtime-слой `cli_runtime.py`, orchestration `cli_parser_core.py`, доменные parser-модули `cli_parser_projects.py`, `cli_parser_agents.py`, `cli_parser_localai.py`, `cli_parser_chains.py`, `cli_parser_registry.py`, `cli_parser_git.py`, `cli_parser_session.py`, а также общие parser-модули `cli_parser_health.py`, `cli_parser_batch.py`, `cli_parser_tools.py`. Точечная чистка фасада/runtime и микроклининг CLI контракт-тестов выполнены без изменения поведения; в `quality summary` добавлен gate `no_secrets` (guardrails json + scan tracked/reports, оценка только secret_scan-*), в README/CODE_REVIEW добавлен runbook `public-readiness -> apply branch protection`, `tools/apply_branch_protection.py` получил precondition-диагностику `private -> feature_unavailable_plan`, затем переведён на rulesets-поток без 404 для текущего репозитория, а `quality public-readiness` — явный `repo_visibility` gate.
- Покрытие целевых модулей техдолга доведено: `cli_cmd_algotrading.py` — 78%, `cli_cmd_obsidian.py` — 94%, `cli_cmd_localai.py` — 90%, `tslab_offline_csv.py` — 99%.
- В окружении могут встречаться ACL-аномалии во временных папках (исключайте `.tmp/` из проверок).

## Post-Reset Plan
1. (done) Разбить `app.py` на модули (`scan.py`, `git_ops.py`, `agents_ops.py`, `run_ops.py`, `cli.py`) без изменения поведения.
2. (done) Добавить `agents status --only-problems --fix-hints` (подсказки команд для проблем, без авто-исправлений).
3. (done) Ввести строгий preflight roots: статусы `ok/missing/access_denied` и флаг `--strict-roots` для batch-команд.
4. (done) Оформить `OPERATIONS_QUICKSTART.md` и добавить smoke-тесты (discovery, only-problems, json-strict).

## Skill Routing
- `integrator-cli-engineer`: любые изменения CLI, команд, контрактов вывода и quality checks.
- `justdoit`: базовое execution-планирование и контроль выполнения нетривиальных задач.
- `localai-assistant-ops`: задачи по LocalAI assistant, RAG, SSOT и индексации.
- `knowledge-governance-ops`: governance баз знаний (Agent Memory, Obsidian, GitHub memory-loop, traceability).
- `security-ops`: baseline security-аудит, hygiene и hardening.
- `stealth-nexus-ops`: VPS/proxy-цепочки и операционные скрипты Stealth Nexus.
- `vpn-manager-maintainer`: задачи проекта `vpn-manager`.
- `vpn-manager-fedora-maintainer`: задачи проекта `vpn-manager-fedora`.
- `github-pr-reviewer`: PR-review по стандарту GitHub перед merge.
- `github-security-reviewer`: security-review auth/API/integration изменений.
- `architecture-advisor`: архитектурные решения и trade-off для LocalAI assistant.
- `code-analyzer`: статический/динамический анализ кода LocalAI assistant.
- `dependency-manager`: зависимости, CVE triage и version conflicts LocalAI assistant.
- `memory-manager`: жизненный цикл долговременной памяти LocalAI assistant.
- `metrics-manager`: KPI/SLI и тренды качества LocalAI assistant.
- `performance-optimizer`: профилирование и оптимизация производительности LocalAI assistant.
- `predictive-debugger`: диагностика интермитентных сбоев и анализ трасс.
- `rag-diagnostics`: компактная RAG-диагностика `/health` и `/_build`.
- `test-generator`: сценарии тестирования и риск-ориентированное покрытие.
