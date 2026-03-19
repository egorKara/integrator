# Policy Migration Path (research/coding/ops)

## Scope
- Документ определяет, как эволюционировать профили `research/coding/ops` без breaking changes.
- Применяется к `workflow zapovednik health` и `workflow zapovednik append --auto-finalize-on-threshold`.

## Versioning Rules
- Версия профилей следует `policy_version: MAJOR.MINOR`.
- `MINOR` повышается при безопасной калибровке порогов в существующих профилях.
- `MAJOR` повышается при удалении профиля, переименовании профиля или смене семантики поля.
- Значение по умолчанию (`coding`) не меняется в рамках одного `MAJOR`.

## Compatibility Rules
- Имена профилей (`research`, `coding`, `ops`) считаются частью публичного CLI-контракта.
- Явные пороговые флаги (`--message-soft-limit`, `--token-hard-ratio` и т.д.) всегда приоритетнее профиля.
- Для каждого изменения профиля обязателен regression-test:
  - проверка `thresholds` в `zapovednik health --json`;
  - проверка override-приоритета CLI-флагов;
  - проверка `recommend_close` на контрольных данных.

## Rollout
- Шаг 1: добавить/обновить тесты и валидировать на локальных smoke-сценариях.
- Шаг 2: обновить документацию профилей и changelog.
- Шаг 3: включить изменения в CI и убедиться, что required checks зелёные.
- Шаг 4: анонсировать изменение с пометкой `policy_version`.

## Deprecation
- Для удаления/переименования профиля сначала вводится период совместимости:
  - минимум один релизный цикл профиль поддерживается как alias;
  - документация содержит дату планируемого удаления.
- После завершения периода совместимости повышается `MAJOR`.
