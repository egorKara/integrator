# integrator — правила v2.0 (Verified)

## Цель и Философия
Единый CLI-интегратор проектов (дефолт: `C:\vault\Projects`, `C:\LocalAI`): **безопасно, предсказуемо, тестируемо**.
Каждое действие агента должно быть **атомарным**, **проверяемым** и **обратимым**.
Используется принцип **T+A=S** (Тезис + Антитезис = Синтез) для любого изменения.

## Суть и Архитектура
- **Core:** Stdlib-ядро Python; read-only по умолчанию; выполнение только через явные команды (`run`/`exec`).
- **Discovery:** `--max-depth`, пропуск тяжёлых директорий, определение "проекта" по маркерам (`.git`, `pyproject.toml`, `package.json`).
- **CLI Contract:**
  - Имя всегда `integrator`.
  - Вывод: табличный (human) + `--json` (machine, JSONL).
  - Стабильный порядок сортировки.
  - Управление: `--dry-run` (план), `--continue-on-error` (batch), `--project` (фильтр).
- **Automation:** Агрегация статусов (`report`), массовые операции (`run`), GitHub (только локальные remotes).

## Протокол Верификации (Verification Loop)
**Агент ОБЯЗАН:**
1. **Plan:** Перед изменением кода сформулировать план или spec.
2. **Execute:** Внести изменения минимальными шагами.
3. **Verify:**
   - Запустить тесты: `python -m unittest discover -s tests`.
   - Проверить линтеры: `python -m ruff check .`, `python -m mypy .`.
   - Проверить функциональность: запуск измененной команды (например, `integrator doctor`).
4. **Iterate:** Если проверка не прошла, откатить или исправить, используя лог ошибки.

## Базовый каркас проекта
- `.trae/` (обязателен): `rules/` (контекст), `skills/` (инструменты), `memory/` (история).
- `project_memory.xml`: Identity, Roots, Output, Run config.
- **Skills:** Минимум один skill на проект с четкой зоной ответственности.
- **Git:** Обязателен. Чистый `git status` перед сложными изменениями.
- **Environment:** Переменные окружения через `.env`. Секреты — **никогда** в коде.

## Безопасность и Доступ
- **Security Ops:** Skill `security-ops` включен во все проекты.
- **Quick Check:** `security_quick_check.ps1` для быстрой диагностики.
- **Paths:** Использовать относительные пути или env-переменные (`LOCALAI_ROOT`, `VAULT_ROOT`). Абсолютные пути (`C:\...`) запрещены в коде, разрешены только в `.env` и конфигах IDE.

## LocalAI и RAG (Спецификация)
- **Root:** `${LOCALAI_ROOT}` (дефолт `C:\LocalAI`).
- **Code:** `C:\LocalAI\assistant`.
- **Artifacts:** `C:\LocalAI\logs`, `C:\LocalAI\cache`, `C:\LocalAI\vector_db*`, `C:\LocalAI\ingest`, `C:\LocalAI\backups` — вне репозиториев и исключены из Git.
- **SSOT:** Единый источник истины конфигурации — `${VAULT_ROOT}\LocalAI\10-Config.md`.
- **RAG Proxy:** Запуск через `integrator localai assistant rag`. Использует chunking, re-ranking и vector search.

## Заповедник Промтов (Memory)
- **Session Start:** Создать `.trae\memory\Заповедник промтов - <TIMESTAMP>.md`.
- **Основной старт цикла:** `workflow zapovednik append` без `--path` (append-first).
- **Автопереход:** после `workflow zapovednik finalize` следующий `append` без `--path` автоматически создаёт новую сессию.
- **Health-контур:** `workflow zapovednik health --json` использовать как machine-checkable источник `recommend_close`.
- **Auto-finalize:** `workflow zapovednik append --auto-finalize-on-threshold --json` разрешён для автоматического закрытия перед append по порогам.
- **Fallback-команда старта:** `python -m integrator session open --json`.
- **Контракт fallback-старта:** использовать поля `success`, `path`, `path_masked` из JSON-ответа.
- **Машинная валидация:** табличный вывод не использовать как источник проверки.
- **Log:** Записывать эффективные промты и стратегии.
- **Session End:** Выполнять `docs/SESSION_CLOSE_PROTOCOL.md` полностью: глубокий самоанализ `T+A=S`, reconciliation устаревших/противоречивых правил, сохранение `session_close_YYYY-MM-DD.md` + `.json`, синхронизация трекера/отчёта и обновление Core Memory (`manage_core_memory`).
- **Session End entrypoint:** `python -m integrator session close --json` (допустимы `--task-id`, `--skip-quality`, `--dry-run` по необходимости).

## Дефолты и Инструменты
- **Check:** `python -m unittest discover -s tests -p "test*.py"`.
- **Lint:** `ruff check .`, `mypy .`.
- **Search:** Использовать `integrator rg` если нативный поиск недоступен.
