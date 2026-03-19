# P0 Recovery: GitHub 401 auth_error

## Диагноз (факт)
- Источник токена в рантайме: переменная окружения `GITHUB_TOKEN`.
- Признак проблемы: `github_snapshot` и `projects-migration-readiness` возвращали `401`.
- Проверка `GET /user` с этим токеном: `401 Bad credentials`.

## Причина
- В окружении был установлен невалидный/устаревший `GITHUB_TOKEN`.
- Из-за приоритета загрузки он перекрывал рабочий токен из файла секретов.

## Исправление (применено)
1) Удалён `GITHUB_TOKEN` из текущей сессии.
2) Явно задан `INTEGRATOR_GITHUB_TOKEN_FILE=C:\Users\egork\.integrator\secrets\github_token.txt`.

## Проверка до/после
- До: `github_snapshot` -> `401`, `projects-migration-readiness` -> `github_api_unavailable`.
- После: `github_snapshot` -> `issues_open_count=0, pulls_open_count=0`.
- После: `projects-migration-readiness` -> `ok=true`, `recommend_projects_migration=false`.

## Точечный план закрепления
1) Убрать устаревший `GITHUB_TOKEN` из пользовательских/system env.
2) Оставить источник токена через файл секретов (`INTEGRATOR_GITHUB_TOKEN_FILE`).
3) Перед рабочим циклом выполнять pre-check:
   - `python -m integrator quality github-snapshot --repo egorKara/integrator --state open --json`
4) При повторном `401` сначала проверять источник токена и только затем права repo.
