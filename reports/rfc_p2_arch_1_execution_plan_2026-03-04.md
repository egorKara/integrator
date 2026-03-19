# RFC P2-ARCH-1 — Execution Plan (machine-checkable)

- Plan ID: `RFC-P2-ARCH-1-EXEC-2026-03-04`
- RFC: `P2-ARCH-1`
- Дата фиксации: `2026-03-04`
- JSON-источник (SSOT): `reports/rfc_p2_arch_1_execution_plan_2026-03-04.json`
- Ограничения: сохраняются контракты `--json`, `--json-strict` и backward compatibility.

## Фазы и сроки

| Фаза | Период | Длительность | Ключевой результат |
|---|---|---:|---|
| P1 — Event Specification and Schema | 2026-03-05 → 2026-03-07 | 3 дн | JSON-schema и валидация событий |
| P2 — Event Log and Rotation | 2026-03-08 → 2026-03-11 | 4 дн | JSONL-журнал и ротация |
| P3 — Read Models for Status and Report | 2026-03-12 → 2026-03-16 | 5 дн | Проекции для `agents status` и `report` |
| P4 — Opt-in CLI Rollout | 2026-03-17 → 2026-03-21 | 5 дн | `events emit/replay/inspect` |

## Метрики контроля

| Metric ID | Target | Сравнение | Источник проверки |
|---|---:|---|---|
| schema_validation_pass_rate | 100 | >= | tests/test_event_schema.py |
| cli_contract_regressions | 0 | = | tests/test_cli_contracts_golden.py |
| event_append_success_rate | 100 | >= | tests/test_events_log.py |
| rotation_overflow_incidents | 0 | = | tests/test_events_rotation.py |
| legacy_output_parity | 100 | >= | tests/test_cli_contracts_golden.py |
| status_projection_failures | 0 | = | tests/test_agents_ops.py |
| new_commands_contract_tests_passed | 100 | >= | tests/test_cli_contracts_golden.py |
| p95_latency_degradation_pct | 15 | <= | reports/perf_baseline_*.json |

## Риски и триггеры

| Risk ID | Риск | Вероятность | Влияние | Триггер-метрика | Порог |
|---|---|---|---|---|---:|
| R1 | Дрейф JSON/JSONL-контрактов | medium | high | cli_contract_regressions | 0 |
| R2 | Деградация latency событийного контура | medium | medium | p95_latency_degradation_pct | 15 |
| R3 | Операционная непрозрачность потока событий | low | high | missing_artifacts_count | 0 |

## QC минимум

```bash
python -m ruff check .
python -m mypy .
python -m unittest discover -s tests -p "test*.py"
python -m integrator perf check --max-degradation-pct 15
```

## Связанные артефакты

- `reports/priority_execution_tracker_2026-03-04.csv` (задача B12).
- `reports/priority_execution_report_2026-03-04.md#b12-completed` (результаты, QC, риски, ссылки).
