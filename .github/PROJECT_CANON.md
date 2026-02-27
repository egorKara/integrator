# PROJECT_CANON.md

## Purpose
- Дать агенту и человеку долговременную “оперативную память” о задачах через GitHub Issues.
- Дать единую точку входа по нескольким репозиториям через GitHub Project.
- Обеспечить воспроизводимость: каждое закрытие задачи подтверждается фактами (verify), а долговременные решения живут в SSOT/доках, а не в чате.

## Principles (T+A=S)
- Тезис: фиксируем текущее состояние и цель фактами.
- Антитезис: фиксируем риски/неизвестные/ограничения.
- Синтез: фиксируем решение и следующий атомарный шаг.
- Атомарность: “Next atomic step” всегда один и без ветвлений.
- Верификация: закрываем работу только с доказательствами (команды/чеки/артефакты) либо с явным исключением и причиной.

## Scope
- Issue = оперативная память задачи (контекст, состояние, verify, next step).
- Project = дашборд внимания (агрегация, приоритеты, статусы, поля).
- SSOT/Docs = долговременная истина (контракты, правила, архитектурные решения).

## Quickstart
1) Создай issue через форму (Task/Bug/Decision).
2) Проставь `type:*`, `area:*`, `tracked`.
3) Заполни “Next atomic step” и “Верификацию (Planned минимум)”.
4) Веди задачу в Project: Backlog → Ready → In Progress → Review/Verify → Done.

## Project Fields (canonical)

### Single select
- Status: Backlog | Ready | In Progress | Blocked | Review-Verify | Done | Parked
- Type: Task | Bug | Decision | TechDebt | Ops
- Priority: P0 | P1 | P2 | P3
- Area: cli | localai | rag | vpn | docs | tests | infra
- Risk: Low | Med | High
- Verification: None | Planned | Running | Passing | Needs Follow-up
- SSOT Impact: None | Update | New Page

### Text
- Next atomic step: одна строка (дублирует next step из issue)
- Blocker: одна строка (заполняется при Status=Blocked)

### Optional
- Effort (number): 1 | 2 | 3 | 5 | 8
- Target (date): целевая дата (если нужна)

## Labels (canonical)

### Type (exactly one)
- type:task
- type:bug
- type:decision
- type:techdebt
- type:ops

### Area (one, максимум два)
- area:cli
- area:localai
- area:rag
- area:vpn
- area:docs
- area:tests
- area:infra

### State (служебные)
- tracked (добавлять в общий Project)
- state:ready (есть next step и verify planned)
- state:blocked (есть блокер)
- state:needs-verify (есть изменения, нет доказательств verify)

### QA (по необходимости)
- qa:needs-test
- qa:regression-risk

### Security (редко, но строго)
- sec:review (затрагивает auth/секреты/периметр/права)

## Workflows

### Light mode (recommended default)
**Цель:** быстрый выигрыш без сложной автоматики.
- Auto-add: issue с `tracked` автоматически добавляется в Project.
- Статусы/поля: руками (перетаскивание карточек, ручной выбор значений).
- Gate для Ready: заполнены T+A=S, Next atomic step, Verify (минимум Planned).
- Gate для Done: Verification=Passing (или явное исключение с причиной) + evidence в issue.

### Strict mode (when ready)
**Цель:** Project отражает фактическое состояние автоматически.
- Auto-add: как в Light.
- Sync state→status:
  - `state:blocked` ⇄ Status=Blocked и заполнен Blocker.
  - `state:ready` ⇄ Status=Ready и заполнен Next atomic step.
  - `state:needs-verify` ⇄ Status=Review-Verify и Verification=Needs Follow-up.
- Sync close→done:
  - закрытие issue переводит карточку в Done, если Verification=Passing или указано исключение.
- Рекомендованный порядок внедрения: Blocked/Unblocked → Done on close → остальное.

## Definition of Done (DoD)

### type:task
- Результат реализован и соответствует “Синтезу”.
- В issue обновлены “Сделано/Осталось” и добавлены доказательства.
- Verify: отмечены lint/tests/smoke (или явное исключение с причиной).
- Перечислены и проверены разумные регрессии.
- Если затронут контракт/правило: SSOT Impact не None и в issue есть ссылка на SSOT.

### type:bug
- Есть симптом и Expected vs Actual.
- Есть воспроизведение (или объяснение, почему невозможно).
- Фикс безопасен и объяснён коротко.
- Есть проверка: тест (желательно) или воспроизводимый smoke + регрессии.
- Есть доказательства (логи/артефакты/ссылки на строки кода) без секретов.

### type:decision
- В issue зафиксированы: решение, альтернативы, последствия.
- Есть ссылка на SSOT (обязательна) и SSOT обновлён.
- Определены follow-ups (миграции/доки/коммуникация).
- Если затрагивает безопасность: проставлен `sec:review` и описаны меры.

## Security hygiene (non-negotiable)
- Секреты/токены/пароли/ключи: никогда не писать в issue/PR/логи/скриншоты.
- Secrets хранить только в GitHub Secrets / локальном `.env` (не коммитить).
- Доказательства верификации: редактировать/редактировать (redact) перед публикацией.
- Для токенов автоматики использовать минимальные права и отдельный бот-аккаунт.
- Любые изменения прав доступа, auth, perimeter: всегда `sec:review`.

## File locations (this repo)
- Canon: `.github/PROJECT_CANON.md`
- Issue Forms: `.github/ISSUE_TEMPLATE/*.yml`
- PR template: `.github/pull_request_template.md`
