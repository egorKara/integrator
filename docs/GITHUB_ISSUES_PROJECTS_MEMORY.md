# GitHub Issues + Projects как внешняя память агента

## Тезис
- Сессионный контекст LLM исчезает, а задачи живут неделями.
- GitHub Issue хранит состояние, решения, ссылки на код и доказательства верификации.
- GitHub Project агрегирует issues из многих репозиториев и становится единой доской внимания.

## Выжимка сути (практика)
- Issue используется как “промпт” и точка восстановления: агент читает issue и продолжает работу из его полей и комментариев.
- Project используется как агрегатор: статусы, приоритет, тип, effort, фильтры и представления.
- Управление делается программно: создать issue, добавить комментарий, закрыть issue, обновить статусы.

Источник: https://sereja.tech/blog/github-projects-ai-agent-memory/

## Что уже есть в этом репозитории (проверено)
- Канон процесса Issues/Projects: [.github/PROJECT_CANON.md](file:///c:/integrator/.github/PROJECT_CANON.md)
- Шаблон issue под “оперативную память задачи” (T+A=S, verify, next step): [memory-task.yml](file:///c:/integrator/.github/ISSUE_TEMPLATE/memory-task.yml)
- Упоминание канона в карте правил: [RULES_MAP.md](file:///c:/integrator/docs/RULES_MAP.md)
- Внутренняя “память” для локальной инфраструктуры (RAG memory-write): [agent_memory_client.py](file:///c:/integrator/agent_memory_client.py), CLI: [cli.py](file:///c:/integrator/cli.py)
- Интеграции integrator CLI с GitHub Issues/Projects нет (в core-командах отсутствуют сетевые вызовы GitHub).

## Что добавлено сейчас (применение лучшего без gh CLI)
- Портативный tool для работы с issue через GitHub REST API:
  - [gh_issue_memory.py](file:///c:/integrator/tools/gh_issue_memory.py)
  - Библиотека операций: [github_issues.py](file:///c:/integrator/github_issues.py)
- Модель безопасности наследуется от общего GitHub REST клиента: [github_api.py](file:///c:/integrator/github_api.py)

## Синтез (канонический рабочий цикл без ветвлений)
1) Создайте issue по шаблону “Memory Task (T+A=S)”.
2) Назначьте лейблы: `type:task`, `tracked`, один `area:*`.
3) Заполните “Next atomic step” и “Верификация (Planned)”.
4) Добавьте issue в общий Project по канону и ведите по статусам до Done.
5) Закрывайте issue только после Verification=Passing и с доказательствами без секретов.

## Команды (портативно, без установки gh)

### Create (dry-run)
```powershell
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<token>"
python tools/gh_issue_memory.py create --title "Task: ..." --body-file .\docs\some_task.md --labels type:task tracked area:cli --dry-run
```

Артефакт: `reports/gh_issue_memory_*.json` (в body не выводится содержимое).

### Create (реально)
```powershell
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<token>"
python tools/gh_issue_memory.py create --title "Task: ..." --body-file .\docs\some_task.md --labels type:task tracked area:cli
```

Артефакт: `reports/gh_issue_memory_*.json` с `issue_number` и `issue_url`.

### Comment
```powershell
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<token>"
python tools/gh_issue_memory.py comment --issue 123 --body-file .\reports\verify.md
```

### Close
```powershell
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<token>"
python tools/gh_issue_memory.py close --issue 123
```

## Антитезис (качество и безопасность)
- Токены не публикуются: токен берётся из env или файла и нигде не печатается.
- Приватные репозитории маскируются как 404 при отсутствии прав; диагностика хранится в `reports/*.json`.
- Любые доказательства в issue проходят редактирование (redact), секреты остаются только в Secrets или локальном `.env`.

## Верификация (факты)
- Тесты: [test_github_issues.py](file:///c:/integrator/tests/test_github_issues.py), [test_github_api.py](file:///c:/integrator/tests/test_github_api.py)

