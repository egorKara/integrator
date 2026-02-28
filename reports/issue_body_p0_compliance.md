## Тезис
В репозитории уже есть минимальные меры безопасности: `.env` исключён из git, присутствует `.env.example`, CI запускает `gitleaks` и `pip-audit`.

## Антитезис (факты)
- **Проверено:** отсутствуют `LICENSE/NOTICE/PRIVACY/TERMS` в репозитории. Подтверждение: листинг корня [C:\integrator](file:///C:/integrator) (файлов нет).
- **Проверено:** в `pyproject.toml` нет поля `project.license` и нет license classifiers. Источник: [pyproject.toml](file:///C:/integrator/pyproject.toml#L1-L21).
- **Проверено:** код выполняет сетевые передачи контента (memory write) и создание Issues через GitHub API. Источники: [agent_memory_client.py](file:///C:/integrator/agent_memory_client.py#L36-L107), [github_issues.py](file:///C:/integrator/github_issues.py#L39-L70).

## Синтез (задачи)
- [ ] **P0** Добавить `LICENSE` в корень и указать лицензию в метаданных (`pyproject.toml`).
- [ ] **P0** Добавить `PRIVACY.md` с явным описанием: какие данные отправляются по сети, куда пишутся локальные артефакты (`reports/`), как передаются токены.
- [ ] **P1** Добавить `NOTICE`/`THIRD_PARTY_NOTICES` под распространяемые компоненты (включая operator requirements) и закрепить процесс обновления.
- [ ] **P1** Усилить `guardrails.py` паттернами для типовых токенов (GitHub PAT и др.), покрыть тестом.

## Acceptance criteria
- В репозитории присутствуют `LICENSE` и `PRIVACY.md`, и они упоминаются в `README.md`.
- `python -m unittest discover -s tests -p "test*.py"` проходит.
- `python -m ruff check .` и `python -m mypy .` проходят.

## Rollback
- `git restore --source=HEAD -- LICENSE PRIVACY.md pyproject.toml README.md guardrails.py` для отмены правок.
