## ✅ CI/релиз: build+wheel smoke+Windows+version

- CI: добавлен `build` job (sdist+wheel, `twine check`, установка wheel в чистое окружение, smoke `integrator --version`, smoke `chains/registry`).
- CI: добавлен `test-windows` job (ruff+mypy+unittest+guardrails).
- Guardrails в CI теперь включает `--scan-tracked`.
- Версия пакета переведена в `dynamic` и берётся из `version.__version__` (без дублирования в `pyproject.toml`).
- `chains.json`/`registry.json`: добавлен embedded fallback через `integrator_resources.py`, чтобы ресурсы были доступны после установки wheel.
- Добавлен release workflow по тегам `vX.Y.Z` с публикацией dist-артефактов в GitHub Releases.

### Локальная верификация
- `python -m ruff check .`
- `python -m mypy .`
- `python -m unittest discover -s tests -p "test*.py"` (171 tests, OK)
- Build+install smoke выполнен через venv: сборка dist, `twine check`, установка wheel, проверка `integrator --version == importlib.metadata.version("integrator")`, smoke `integrator chains list --json` и `integrator registry list --json`.

### Изменённые файлы
- .github/workflows/ci.yml
- .github/workflows/release.yml
- pyproject.toml
- integrator_resources.py
- chains.py
- registry.py
- tests/test_chains.py
- tests/test_registry.py
