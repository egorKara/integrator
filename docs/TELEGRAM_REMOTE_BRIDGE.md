# Telegram Remote Bridge

## Назначение
- Дать удалённый канал со смартфона: отправлять задачи в проект и получать статус без открытия IDE.

## Что реализовано
- Скрипт: `python -m tools.telegram_remote_bridge`.
- Поддерживаемые команды в Telegram:
  - `/task <текст>` — создаёт GitHub Issue в целевом репозитории;
  - `/reply <event_id> <текст>` — отвечает в поток (комментирует issue, если он уже связан с событием);
  - `/inbox [N]` — показывает последние входящие события с `event_id` для reply;
  - `/status` — краткий статус board `project_top6_priorities`;
  - `/next` — следующий приоритет из board;
  - `/help` — справка.
- Скриншоты:
  - можно отправить скриншот с подписью `/task <описание>` и bridge добавит вложение в тело issue;
  - скриншот без подписи сохраняется в inbox, затем используйте `/reply <event_id> <текст>`.
- Артефакты:
  - `reports/telegram_bridge_events.jsonl` — журнал команд/ответов;
  - `reports/telegram_bridge_offset.txt` — checkpoint update offset.

## Минимальная настройка
- Создать бота через `@BotFather`.
- Настроить переменные окружения:
  - `TELEGRAM_BOT_TOKEN` — токен бота;
  - `TELEGRAM_BRIDGE_REPO` — `owner/repo` для issue;
  - `TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS` — список chat_id через запятую.
- Убедиться, что доступен GitHub токен через `GITHUB_TOKEN_FILE` или стандартные пути integrator.

## Единоразовый приём секретов
```powershell
Set-Location C:\integrator
.\scripts\setup_integrator_secrets.ps1 -Json
```

- Скрипт проверяет валидность `TELEGRAM_BOT_TOKEN` и `GITHUB_TOKEN`.
- GitHub токен сохраняется в `%USERPROFILE%\.integrator\secrets\github_token.txt`.
- В user env сохраняются только маршрутизирующие параметры и путь к токену (`GITHUB_TOKEN_FILE`, `INTEGRATOR_GITHUB_TOKEN_FILE`).

## Запуск
```powershell
python -m tools.telegram_remote_bridge --once --json
```

```powershell
python -m tools.telegram_remote_bridge --json
```

## One-click запуск без ручной копипасты
```powershell
Set-Location C:\integrator
.\scripts\start_telegram_bridge.ps1 -Persist -Once -DryRun -Json
```

```powershell
Set-Location C:\integrator
.\scripts\start_telegram_bridge.ps1 -Persist -Json
```

- Скрипт запросит `Telegram Bot Token`, `GitHub Token`, `chat_id` и `repo` только если значения не найдены в Process/User env.
- С `-Persist` значения сохраняются в user env и переиспользуются в следующих запусках.
- Режим только конфигурации без запуска bridge:
```powershell
.\scripts\start_telegram_bridge.ps1 -Persist -ConfigureOnly -Json
```

## Постоянный автозапуск (Windows, user-level)
```powershell
Set-Location C:\integrator
.\scripts\manage_telegram_bridge_task.ps1 -Action install
```

```powershell
.\scripts\manage_telegram_bridge_task.ps1 -Action status
.\scripts\manage_telegram_bridge_task.ps1 -Action restart
.\scripts\manage_telegram_bridge_task.ps1 -Action uninstall
```

- Задача `IntegratorTelegramBridge` стартует на logon и перезапускает bridge при выходе.
- Фоновый лог процесса: `reports/telegram_bridge_logs/bridge.log`.
- Для ручного запуска используйте `--once`; постоянный режим оставьте только Scheduled Task.

## Регулярное сканирование GitHub задач из Telegram
```powershell
Set-Location C:\integrator
.\scripts\manage_telegram_github_worker_task.ps1 -Action install
```

```powershell
.\scripts\manage_telegram_github_worker_task.ps1 -Action status
.\scripts\manage_telegram_github_worker_task.ps1 -Action restart
.\scripts\manage_telegram_github_worker_task.ps1 -Action uninstall
```

- Воркер сканирует open issues с labels `remote,telegram`.
- Новые issue ставятся в локальную очередь `reports/telegram_github_worker_queue.jsonl`.
- В issue добавляется label `agent:queued` и комментарий о постановке в очередь.
- Авто-исполнитель переводит `agent:queued` в `agent:in_progress` и создаёт локальный execution-plan.
- Состояние дедупликации хранится в `reports/telegram_github_worker_state.json`.
- Состояние авто-старта исполнения хранится в `reports/telegram_github_executor_state.json`.
- Планы исполнения создаются в `reports/telegram_issue_execution_plans/`.
- Фоновый лог воркера: `reports/telegram_github_worker_logs/worker.log`.

## Security baseline
- Без `TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS` запуск запрещён.
- Для первых прогонов использовать `--dry-run`.
- Токены хранить только в env/secrets, не в репозитории.
- Если бот отвечает `status=401 kind=auth_error`, перезапустите launcher и обновите `GITHUB_TOKEN`.
- Если бот отвечает `HTTP Error 409: Conflict`, уже работает другой экземпляр long-poll; оставьте один процесс через Scheduled Task.

## GitHub Projects модель
- Подробный разбор возможностей Projects и целевая модель применения в integrator: `docs/GITHUB_PROJECTS_DEEP_RESEARCH_RU.md`.
