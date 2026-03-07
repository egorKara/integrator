# SLI/SLO integrator

## Область
- Локальная эксплуатация CLI `integrator`.
- Доступность внешних сервисов для preflight (`RAG`, `LM Studio`).
- Стабильность quality/CI контуров.

## SLI
- `preflight.rag.ok`: доля успешных health-check `RAG`.
- `preflight.lm_studio.ok`: доля успешных health-check `LM Studio`.
- `perf.projects_list.median_ms`: медиана latency команды `projects list`.
- `perf.status.any_failed`: бинарный индикатор ошибок в baseline для `status`.
- `perf.degradation_pct`: относительная деградация latency по метрикам baseline.
- `quality.total_coverage_pct`: общее покрытие по `coverage report`.
- `github.open_issues_count` и `github.open_pulls_count`: снимок состояния внешнего бэклога.

## SLO
- `preflight.rag.ok >= 99%` на выборке ежедневных запусков.
- `preflight.lm_studio.ok >= 99%` на выборке ежедневных запусков.
- `perf.status.any_failed = false` на nightly baseline.
- `perf.degradation_pct <= 20%` относительно последнего подтверждённого baseline.
- `quality.total_coverage_pct >= 80`.
- `github_snapshot` формируется минимум 1 раз в день и сохраняется в `reports/github_snapshot_*.json`.

## Процедура измерения
```powershell
python -m integrator preflight --json
python -m integrator perf baseline --json --roots . --write-report reports\perf_baseline_current.json
python -m integrator perf check --baseline reports\perf_baseline_reference.json --current reports\perf_baseline_current.json --max-degradation-pct 20 --json
python -m coverage run -m unittest discover -s tests -p "test*.py"
python -m coverage report -m --fail-under=80
python -m integrator quality github-snapshot --repo egorKara/integrator --json
```

## Артефакты
- `reports/perf_baseline_*.json`
- `reports/github_snapshot_*.json`
- `reports/coverage.xml`
- `results.sarif`
