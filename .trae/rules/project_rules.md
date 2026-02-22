# integrator — правила

## Цель
Единый CLI-интегратор проектов (дефолт: `C:\vault\Projects`, `C:\LocalAI`): безопасно, предсказуемо, тестируемо.

## Суть
- Stdlib-ядро; по умолчанию read-only; выполнение только явно (`exec/run`).
- Скан: `--max-depth`, skip тяжёлые dirs, “проект” по маркерам (`.git`, `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, …).
- `run lint|test|build`: команды по наличию конфигов/скриптов/инструментов; нет плана → skip.
- Вывод: таблично + `--json` (JSONL); порядок стабильный.
- Управление: `--dry-run` (план без запуска), `--continue-on-error` (batch).
- Массовые команды: `--project` (фильтр), `--limit`, `--jobs`.
- Агрегация: `report` собирает kind+git+remotes в один проход.
- GitHub: только локальные remotes; нормализация URL; без сети.
- Тесты: `unittest` + temp dirs; `git init` в temp при необходимости.

## Принципы рефакторинга
- Единые хелперы для выбора проектов, лимитов и сортировки.
- Параллельная обработка через общий map без дублирования логики.
- Отдельный фильтр Git-проектов для команд, где нужен VCS-контекст.
- Имя CLI и help всегда `integrator` независимо от argv.
- Единая фильтрация проектов применяется и для `run`.
- Единые функции вывода для JSON и табличных строк.
- Единый запуск внешних команд и проверка путей.
- Единый набор полей Git-статуса для status и report.
- Единый вывод диагностики окружения через хелперы.
- Единый вывод списков проектов через общий хелпер.
- Единая выборка git-проектов для status и remotes.

## Базовый каркас проекта
- `.trae/` обязателен: rules/skills/memory.
- `project_memory.xml` обязателен и содержит identity/roots/output/run.
- Минимум один skill на проект, с ясной зоной ответственности.
- Git обязателен даже без remote, чистый status перед важными действиями.
- Единый формат имен и CLI, не зависящий от argv.
- Переключение LLM/IDE провайдеров обязательно: Trae ↔ Codex без смены ядра.

## Безопасность (минимум)
- Единый security‑skill включён во все проекты.
- Быстрый контроль через `security_quick_check.ps1`.

## MCP/расширения (минимум)
- Обязательный минимум: security-ops + один доменный skill проекта.
- Для проектов, зависящих от LocalAI: localai-assistant-ops и запуск MCP server из `C:\LocalAI\assistant\mcp_server.py`.
- Для integrator: integrator-cli-engineer обязателен.
- Для vpn-manager-fedora: vpn-manager-fedora-maintainer обязателен.

## LocalAI-зависимые проекты (структура)
- Код и документация: `C:\vault\Projects\LocalAI\Deps\<project>`.
- Данные/логи/кэш/векторные базы хранятся вне репозиториев в `C:\LocalAI\logs`, `C:\LocalAI\cache`, `C:\LocalAI\vector_db*`, `C:\LocalAI\ingest`.
- Тяжёлые артефакты подключаются через junction/симлинк и исключаются из индексации IDE.

## Заповедник промтов
- В начале каждой сессии создаётся файл `.trae\memory\Заповедник промтов - YYYY-MM-DD-HHMM.md`.
- Промты записываются и сортируются по задачам.
- После завершения задачи добавляется краткая суммаризация по задаче и оценка эффективности промтов.

## Дефолты
- Roots: `C:\vault\Projects`, `C:\LocalAI` или `INTEGRATOR_ROOTS` (`;`, поддерживается `TAST_ROOTS`).
- Check: `python -m unittest discover -s tests -p "test*.py"`.

## Поиск по кодовой базе (workaround)
- Если в Trae падает встроенный шаг “Search codebase”, используйте поиск через integrator-обёртку (не требует `rg` в PATH):
  - `python -m integrator rg -- "<pattern>" .`
  - Если нужны флаги `rg`, добавляйте `--` и/или отключайте дефолты:
    - `python -m integrator rg -- -n --hidden --glob '!.git' --glob '!vault' --glob '!.trae' "<pattern>" .`
    - `python -m integrator rg --no-defaults -- --version`
- Для точечного поиска по одному файлу используйте встроенный read/open вместо глобального поиска.
