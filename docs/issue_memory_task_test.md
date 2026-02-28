# Memory Task (T+A=S) — TEST

## Тезис (ситуация)
- Нужен тестовый артефакт “issue как память задачи” без реального доступа к GitHub (без токена).

## Антитезис (проблема/риски/неизвестное)
- Без токена нельзя создавать issue в GitHub API, но можно проверить корректность плана запроса и метаданных.
- Секреты не должны появляться в stdout/stderr/артефактах.

## Синтез (решение/подход)
- Сформировать тело issue по шаблону памяти (T+A=S).
- Выполнить `tools/gh_issue_memory.py --dry-run create ...` и сохранить отчёт в `reports/*.json`.

## Контекст
- Репо/модуль: `integrator`
- Цель: проверить “dry-run план” создания issue

## Текущее состояние
- Сделано: создан этот файл
- Осталось: сгенерировать `reports/gh_issue_memory_*.json` через dry-run
- Блокеры: нет

## Верификация
- Ожидаемое поведение: создаётся отчёт с URL `/repos/{owner}/{repo}/issues`, корректными label’ами и `token_present=false`.
- Чеки:
  - `python tools/gh_issue_memory.py --dry-run create --title "[Task]: TEST dry-run issue" --body-file .\docs\issue_memory_task_test.md --labels type:task tracked area:docs`

## Next atomic step
Запустить dry-run и проверить `reports/gh_issue_memory_*.json`.
