# Top-6 приоритетов проекта (2026-03-04)

## Контекст
- Назначение: единый управленческий board для последовательного исполнения приоритетов после завершения B1-B15.
- Принцип: сначала Blocker/High, затем Medium; переход вниз только при `completed` или `blocked`.

## Board

| ID | Приоритет | Направление | Владелец | DoD (критерий готовности) | Gate-метрика | Риск |
|---|---|---|---|---|---|---|
| P12 | High | Governance board и трассировка | AI Agent (Integrator CLI Engineer) | Top-6 board зафиксирован в `MD+JSON`, синхронизирован с tracker/report | `json-parse;tracker-sync;report-anchor-check` | рассинхронизация board и tracker без регулярного обновления |
| P13 | High | JSON/JSON-strict контракт batch-run | AI Agent (Integrator CLI Engineer) | покрыты негативные сценарии stderr/exit-path без поломки JSONL stdout | `contract-tests-pass` | регресс json-strict при изменениях в run-контуре |
| P14 | High | Session close consistency для execution-plan JSON↔MD | AI Agent (Integrator CLI Engineer) | добавлен checker и CI step для план-артефактов RFC | `execution-plan-consistency-pass` | дрейф дат/метрик между JSON и MD |
| P15 | Medium | Калибровка профилей `research/coding/ops` | AI Agent (Integrator CLI Engineer) | профили откалиброваны на выборке сессий, пороги подтверждены тестами | `profile-calibration-report` | пере/недо-чувствительные пороги auto-finalize |
| P16 | Medium | Perf reference baseline (stable env) | AI Agent (Integrator CLI Engineer) | эталон baseline зафиксирован отдельным артефактом и проверяется в CI | `perf-drift-check-pass` | шум CI без стабильного baseline окружения |
| P17 | Medium | EPIC execution kickoff (event-driven + memory) | AI Agent (Integrator CLI Engineer) | фаза-1 EPIC запущена с измеримыми SLI и контуром отката | `phase1-gates-pass` | архитектурный дрейф без rollback дисциплины |

## Порядок исполнения
1. P12 — завершён (board создан и синхронизирован).
2. P13 — завершён.
3. P14 — завершён.
4. P15 — завершён.
5. P16 — завершён.
6. P17 — завершён.
7. Top-6 board закрыт полностью.
