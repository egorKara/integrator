# Skills Path Compatibility

## Цель

Официально зафиксировать соответствие между рабочим каталогом навыков `.trae/skills` и стандартным каталогом `.agents/skills`.

## Политика

1. Источник истины для содержимого навыков: `.trae/skills/**/SKILL.md`.
2. Стандартный слой совместимости: `.agents/skills/skills_map.json`.
3. Для подпроекта LocalAI assistant используется отдельная карта: `LocalAI/assistant/.agents/skills/skills_map.json`.
4. Любое добавление/переименование/удаление навыка обязательно обновляет `docs/SKILLS_INDEX.md`, обе карты соответствий и `AGENTS.md`.
5. Merge baseline для skill-изменений обязателен и описан в `docs/CODE_REVIEW.md`.
6. Машинная проверка согласованности выполняется командой `python -m tools.check_skills_sync --json` локально и в CI.
7. Для новых governance-циклов использовать структуру отчёта `reports/skills_sync_baseline_2026-03-07.md` как шаблон.

## Формат соответствия

- `name`: имя skill.
- `canonical_path`: путь к каноническому SKILL.md в `.trae/skills`.
- `standard_path`: путь в стандартной схеме `.agents/skills`.
- `status`: `active`.
