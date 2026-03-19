# 24/7 AI-комбайн: итоговая рекомендация (2026-03-05)

## Executive summary
- Полностью бесплатный и одновременно надёжный 24/7 AI-контур малореалистичен.
- Реалистичная стратегия: **local-first (LM Studio) + ограниченные external fallback + селективная эскалация в Codex + GitHub Issues как state machine**.
- Главный риск — не отсутствие моделей, а отсутствие строгой policy маршрутизации, budget guardrails и ops-дисциплины.

## Критический анализ исходных тезисов
1. **LM Studio только на маленьких моделях** — верно; это не баг, а архитектурный факт. Значит LM Studio должен быть “default для дешёвых T0/T1”, а не “универсальный мозг”.
2. **Codex быстро ест лимит** — верно; Codex нельзя ставить в default path.
3. **Основная продуктивность в Trae** — верно сейчас, но это одновременно SPOF UX: без IDE теряется реальный “онлайн-ассистент”.
4. **Искать бесплатные сервисы** — полезно, но критично не переоценить: free tiers нестабильны и не имеют жёсткого SLA.
5. **Построить комбайн сложно, но интересно** — верно; сложность оправдана только если есть owner-процессы и fail-safe.

## Архитектурные варианты (decision matrix)

| Вариант | Описание | Плюсы | Минусы | Оценка |
|---|---|---|---|---|
| A Local-first | LM Studio default + внешние fallback + Codex only escalation | Минимальная стоимость, контролируемый контур, предсказуемый burn | Качество на сложных задачах плавает | **8.8/10** |
| B Router-first multi-provider | Агрессивный роутер между free providers + local + Codex | Гибкость, высокая адаптивность | Сложный ops, высокий риск нестабильности free | 7.3/10 |
| C Issue-centric only | Telegram -> GitHub Issues -> ручной/полуручной обработчик | Максимальный аудит и трассировка | Низкая “живость” диалога, выше latency | 6.9/10 |

**Рекомендован вариант A** как первый production baseline.

## Предложенный production baseline (phase-1)
- **Linux Mint**: primary 24/7 host (systemd services, autorestart).
- **OpenClaw**: orchestration runtime + watchdog.
- **Telegram**: единственный UX канал.
- **GitHub Issues**: canonical state/audit/backlog.
- **LM Studio**: default inference.
- **Codex**: строго по escalation policy.
- **Free providers**: fallback-only, с circuit-breaker и лимитами.

## Неудобные, но насущные вопросы (must-answer before rollout)
1. Кто владелец решения о переходе из free в paid режим ночью без ручного подтверждения?
2. Какой точный список данных запрещён к отправке во внешние API?
3. Что считается “качество неприемлемо” и как это детектируется автоматически?
4. Какой максимальный допустимый Codex burn/day и что происходит после достижения?
5. Какой recovery path при одновременном падении OpenClaw и внешнего fallback?
6. Кто и как подтверждает, что Telegram-команда “действительно выполнена”, а не зависла в retry?
7. Как не превратить комбайн в дорогой в сопровождении “конструктор” без ROI?

## Go / No-Go критерии

### Go
- Введена и протестирована routing policy (machine-checkable).
- Есть health-check + alerting в Telegram.
- Есть hard budget caps (Codex/day/hour).
- Есть security baseline: token hygiene, allowlist, least-privilege scopes.
- Есть аварийные сценарии с измеряемым MTTR.

### No-Go
- Нет owner-процесса по лимитам/эскалации.
- Нет явной data policy для внешних провайдеров.
- Нет доказуемого восстановления после outage.
- Нет мониторинга деградации качества.

## Рекомендуемый план внедрения (последовательность)
1. Зафиксировать routing policy и hard budgets.
2. Поднять systemd-контур 24/7 на Linux Mint.
3. Подключить GitHub Issue lifecycle как state machine.
4. Подключить free fallback с circuit-breaker.
5. Включить Codex selective escalation.
6. Провести 72h soak test и затем production cutover.

## Ожидаемый эффект
- Снижение зависимости от IDE-присутствия.
- Контролируемый burn лимитов.
- Phone-first UX без ручного дублирования.
- Доказуемая трассировка решений и задач через GitHub Issues.
