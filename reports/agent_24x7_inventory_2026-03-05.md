# Инвентаризация 24/7 контура (2026-03-05)

## 1) Доступные вычислительные и сервисные ресурсы
- **Linux Mint ноут 24/7**: целевой primary host для оркестратора и watchdog.
- **OpenClaw 24/7**: уже установлен и используется как агентный runtime.
- **LM Studio 24/7**: локальный OpenAI-compatible endpoint для дешёвого базового inference.
- **Trae (основной продуктивный агент)**: лучший текущий контур качества.
- **Codex**: доступен, но лимитный и дорогой по “budget burn”.
- **Telegram bridge**: рабочий phone-first канал с `/task`, `/reply`, `/inbox`, скриншотами.
- **GitHub Issues**: готов для state/log/backlog маршрутизации.

## 2) Подтверждённые ограничения
- **Аппаратные лимиты локального inference**: RX 6600 4GB VRAM, 16GB RAM ограничивают размер моделей и устойчивую длину контекста.
- **Локальные модели LM Studio**: пригодны для small/medium задач, но не для универсального high-quality режима.
- **Codex лимит**: нет machine-checkable policy в репозитории, риск быстрого исчерпания на сложных задачах.
- **OpenClaw ops-risk**: фиксировались token mismatch/портовые проблемы/неполная service-дисциплина.
- **Telegram/runtime split**: без автономного оркестратора Telegram не равен “живому 24/7 ассистенту”.

## 3) Текущий baseline по компонентам
- **Telegram bridge**: умеет text+reply+inbox+screenshots и привязку к issue.
- **Issue workflow**: `/task` и `/reply` могут порождать или комментировать issue.
- **Launcher**: есть one-click скрипт с `-Persist` и автозагрузкой env в процесс.
- **LM sidecar**: уже есть режимы recommendations/triage/tests и безопасные guardrails по входным данным.

## 4) Критические операционные риски
- **Single-point on orchestration**: если runtime упал, phone-first UX ломается полностью.
- **Token hygiene**: хранение в user env удобно, но увеличивает attack surface.
- **Provider volatility**: free-сервисы часто меняют лимиты/модели без SLA.
- **Silent degradation**: возможен “ответ есть, качества нет” без quality gate и routing policy.

## 5) Инвентаризация интерфейсов интеграции
- **Telegram**: transport и UX-точка входа.
- **GitHub Issues**: queue/state/audit log.
- **OpenClaw**: execution fabric, cron/daemon/gateway.
- **LM Studio**: default local inference.
- **Codex**: selective escalation.

## 6) Вывод инвентаризации
- Ресурсы достаточны для **гибридного 24/7 комбайна**, но только при строгой policy-маршрутизации и операционной дисциплине.
- Главный дефицит сейчас не “мощность”, а **архитектура контроля лимитов и деградаций**.
