# Memory Task (T+A=S) — CLI: команды чтения agent memory

Связанный отчёт:
- [AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md](file:///C:/integrator/docs/AGENT_MEMORY_CLIENT_REVIEW_2026-02-28.md)

## Тезис (ситуация)
- На сервере доступны read‑эндпоинты.
- В integrator есть только write‑команды (workflow preflight-memory-report и localai assistant memory-write).

## Антитезис (проблема/риски/неизвестное)
- Автоматизациям нужна возможность читать память в машинном формате.
- Нужен стабильный JSONL‑контракт под `--json`.

## Синтез (решение/подход)
- Добавить новые команды под `integrator localai assistant`:
  - `memory-search --q ...`
  - `memory-recent`
  - `memory-retrieve`
  - `memory-stats`
  - `memory-feedback --id ... --rating ...`
- Реализовать `--json` как JSONL:
  - одна запись на stdout = один объект (по аналогии с memory-write)
  - без вывода секретов и без вывода содержимого токена

## Верификация (Planned)
- Unit‑тесты на CLI вывод `--json`.
- Smoke: `python -m integrator localai assistant memory-search --q test --json`

## Next atomic step
Добавить парсеры новых подкоманд и прокинуть вызовы на новые методы клиента.

