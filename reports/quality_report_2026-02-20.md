# Quality Report (2026-02-20)

## Tests
- Command: `python -m unittest discover -s tests -p "test*.py"`
- Result: 35 tests, OK

## Coverage
- Command: `python -m coverage report -m`
- Total: 80%
- XML: `reports/coverage.xml`

## Lint and Typecheck
- Ruff: `python -m ruff check .` -> passed
- Mypy: `python -m mypy . tests` -> passed

## Known Issues and Limitations
- Partial coverage in `run_ops.py` and `agents_ops.py`.
- `python -m mypy . tests` затрагивает `vault/` и падает на внешнем коде, используйте явный список модулей.
- `rag_server.py` uses Flask dev server.
- `Test-NetConnection` output may omit boolean without additional formatting.
