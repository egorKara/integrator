# RFC P2-ARCH-1: Event-Driven Agents для integrator

## Статус
- Принято: 2026-03-04.
- Область: roadmap-пункт `P2-ARCH-1` (переход от только command-driven orchestration к event-driven контуру).

## Цель
- Добавить событийную модель для агентных сценариев без нарушения текущих CLI-контрактов.

## Влияние на CLI-контракты
- Контракт `--json` сохраняется: каждая строка остаётся валидным JSON-объектом.
- Контракт `--json-strict` сохраняется: в `stdout` только JSONL, технический вывод остаётся в `stderr`.
- Существующие команды (`run`, `status`, `report`, `agents status`) сохраняют коды возврата и поля ответов.
- Новые event-driven команды добавляются как отдельные подпарсеры, без изменения поведения существующих.

## Предлагаемые этапы внедрения
1. `Phase 1` — спецификация события (`event_id`, `event_type`, `source`, `payload`, `ts`) и JSON-schema.
2. `Phase 2` — локальный журнал событий в `reports/events_*.jsonl` с ротацией.
3. `Phase 3` — read-model для агрегатов (`agents status`, `report`) из event log.
4. `Phase 4` — opt-in CLI-команды (`events emit`, `events replay`, `events inspect`) и backward-compatible rollout.

## Риски и контроль
- Риск роста сложности: контролируется поэтапным rollout и feature-flag.
- Риск дрейфа контрактов JSON/JSONL: контролируется golden/regression-тестами.
- Риск деградации latency: контролируется `perf baseline` + `perf check --max-degradation-pct`.
- Риск операционной непрозрачности: контролируется обязательными артефактами в `reports/`.

## Критерии принятия решения
- RFC принят без блокеров по security/quality.
- Влияние на контракты CLI признано нулевым для существующих команд.
- План внедрения и риски зафиксированы и трассируются через quality gates.
