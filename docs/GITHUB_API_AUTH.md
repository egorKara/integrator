# GitHub API Auth (private repos)

## Тезис
- Приватные репозитории при обращении к GitHub REST API без корректного токена часто выглядят как `404 Not Found`.
- Безопасный доступ требует токена в `Authorization` и стандартных заголовков GitHub API.

## Что реализовано в integrator (проверено)
- Общий клиент GitHub REST API: [github_api.py](file:///c:/integrator/github_api.py)
  - Извлечение токена: `GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN_FILE`, `INTEGRATOR_GITHUB_TOKEN_FILE`, а также локальный `.env` в корне репозитория (значение токена не печатается).
  - Заголовки: `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, `Authorization: Bearer <token>`.
  - Классификация ошибок: 401/403 как auth error, 404 без токена как “auth missing” (приватное маскирование).
- Проверка доступа и мутации branch protection: [apply_branch_protection.py](file:///c:/integrator/tools/apply_branch_protection.py)
  - Делает precheck `GET /repos/{owner}/{repo}` перед любыми изменениями.
  - Поддерживает безопасный режим проверки доступа: `--check-only`.

## Антитезис (границы и риски)
- Токен с недостаточными правами даёт `404` и `403` и выглядит как “репозиторий не существует”.
- Серии неверных попыток аутентификации приводят к временным отказам (failed login limit) и `403` даже для валидного токена.
- SAML SSO для org при использовании PAT classic требует явной авторизации токена; иначе возникают `404` и `403`.

## Синтез (как использовать)

### Переменные окружения
- `GITHUB_REPOSITORY=owner/repo`
- `GITHUB_TOKEN=<token>` (предпочтительный)
- `GH_TOKEN=<token>` (совместимость)
- `GITHUB_TOKEN_FILE=<path>` (чтение токена из файла)
- `INTEGRATOR_GITHUB_TOKEN_FILE=<path>` (совместимость)

Пример ключей закреплён в [.env.example](file:///c:/integrator/.env.example).

### Локальный .env (персистентно, без вставки токена в команды)
Создайте файл `.env` рядом с `.env.example` и добавьте строку:
```
GITHUB_TOKEN=...
```

### Проверка доступа к приватному репозиторию без мутаций
```powershell
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<token>"
python tools/apply_branch_protection.py --check-only
```

Артефакт: `reports/branch_protection_apply_*.json` с `checks.repo_access.ok=true`.

## Верификация (факты)
- Unit tests: `python -m unittest discover -s tests -p "test*.py"`
- Lint: `python -m ruff check .`
- Typecheck: `python -m mypy .`
- Покрытие хедера `Authorization` и классификации 404: [test_github_api.py](file:///c:/integrator/tests/test_github_api.py)

## Откат
- `git restore --source=HEAD -- github_api.py tools/apply_branch_protection.py .env.example docs/GITHUB_API_AUTH.md`
- `git clean -f -- tests/test_github_api.py`

## Источники
- GitHub REST API authentication: https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api
