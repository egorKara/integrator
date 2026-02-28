## Тезис
CI уже даёт strong gates: ruff, mypy, unittest, coverage ≥80%, gitleaks, pip-audit. Источник: [ci.yml](file:///C:/integrator/.github/workflows/ci.yml).

## Антитезис (факты)
- **Проверено:** CI запускается только на `ubuntu-latest`. Источник: [ci.yml](file:///C:/integrator/.github/workflows/ci.yml#L10-L116).
- **Проверено:** в CI отсутствует сборка wheel/sdist и установка из артефакта. Источник: [ci.yml](file:///C:/integrator/.github/workflows/ci.yml).
- **Проверено:** `chains.json` и `registry.json` читаются как “файлы рядом с модулем”, что рискованно при установке из wheel без package-data. Источники: [chains.py](file:///C:/integrator/chains.py#L17-L24), [registry.py](file:///C:/integrator/registry.py#L20-L27).
- **Проверено:** версия продублирована в `pyproject.toml` и `version.py`. Источники: [pyproject.toml](file:///C:/integrator/pyproject.toml#L5-L10), [version.py](file:///C:/integrator/version.py).

## Синтез (задачи)
- [ ] **P1** Добавить job `build`: `python -m build`, `twine check`, установка wheel в чистое окружение, smoke `integrator --version`.
- [ ] **P1** Сделать ресурсы `chains.json/registry.json` корректными для дистрибутива (package-data или `importlib.resources`) и добавить тест “доступно после установки wheel”.
- [ ] **P1** Убрать дублирование версии и добавить CI-check консистентности версии CLI и metadata пакета.
- [ ] **P1** Добавить Windows job в CI для путей/PowerShell-краёв.
- [ ] **P2** Добавить release workflow по тегам `vX.Y.Z` с публикацией dist-артефактов в GitHub Releases.

## Acceptance criteria
- CI содержит build+install smoke, и он проходит.
- `integrator --version` совпадает с `importlib.metadata.version("integrator")` после установки wheel.
- Windows job проходит тот же набор gates.

## Rollback
- `git restore --source=HEAD -- .github/workflows/ci.yml pyproject.toml version.py` для отмены правок.
