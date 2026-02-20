---
name: "security-ops"
description: "Baseline security checks and hardening guidance for all projects. Invoke for security posture, audit, and hygiene automation."
---

# Security Ops

## Scope
- Базовая безопасность рабочих машин и проектов.
- Единые чек‑листы и минимальная автоматизация проверок.
- Контроль секретов и hygiene Git.

## Источники истины
- Project rules в .trae/rules/project_rules.md
- Локальные политики проекта (если есть)

## Нормальный рабочий цикл
1) Прогон quick‑check.
2) Проверка актуальности патчей и антивируса.
3) Контроль состояния репозиториев и секретов.

## Типовые задачи
- Проверка BitLocker/Veracrypt статуса.
- Проверка Defender и базовой защиты.
- Сводка грязных репозиториев.

## Примеры команд
- Quick check: `pwsh C:\Users\egork\Documents\trae_projects\integrator\.trae\automation\security_quick_check.ps1`
