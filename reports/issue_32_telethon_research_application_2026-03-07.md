# Issue #32 — Telethon: исследование применимости к integrator

## Что такое Telethon в контексте проекта
- Telethon — MTProto-клиент для Telegram (async Python), позволяющий работать не только через Bot API.
- Потенциальная ценность: более гибкие сценарии Telegram automation и прямой контроль контекста взаимодействий.

## Где применимо у нас
- Телеграм-контур уже используется как remote bridge.
- Telethon может быть полезен как опциональный advanced-режим:
  - richer event handling,
  - сценарии, где Bot API ограничивает поток,
  - резервный контур для специфичных операций.

## Риски и ограничения
- Повышение операционной сложности (sessions, auth lifecycle).
- Риск нарушения ToS при некорректном сценарии автоматизации.
- Нужно жёстко развести “bot-safe” и “user-session” режимы.

## Рекомендуемый путь внедрения
1) Phase 1 (safe probe): POC-only модуль без включения в default runtime.
2) Phase 2 (gated pilot): feature flag + явный opt-in + telemetry.
3) Phase 3 (production decision): сравнение SLA/latency/reliability против текущего Bot API контура.

## Критерии go/no-go
- Go:
  - measurable benefit по latency/reliability или функциональной полноте.
  - отсутствие регресса security/operations.
- No-go:
  - усложнение эксплуатации без чёткой прикладной выгоды.
