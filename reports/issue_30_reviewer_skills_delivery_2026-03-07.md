# Issue #30 — Доставка 2 review skills по GitHub-стандарту

## Что реализовано
- Созданы два специализированных skills:
  - `github-pr-reviewer` — функциональный PR-review (контракты, регрессии, готовность к merge).
  - `github-security-reviewer` — security-review (secrets, permissions, API safety, fail-fast).

## Где находятся артефакты
- `.trae/skills/github-pr-reviewer/SKILL.md`
- `.trae/skills/github-security-reviewer/SKILL.md`

## Отличия специализаций
- PR Reviewer:
  - фокус на корректность изменений и совместимость поведения.
- Security Reviewer:
  - фокус на безопасность контуров, токенов, мутаций и rollback.

## Как это закрывает вопрос без внешних GitHub reviewers
- Внутренний review pipeline теперь имеет два устойчивых AI-контекста с разной экспертизой.
- Это позволяет последовательно проводить функциональное и security ревью до merge.

## Где брать “этих спецов”
- В проекте они уже оформлены как skills в `.trae/skills`.
- Для масштабирования можно добавлять новые профильные skills по той же структуре.
