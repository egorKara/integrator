---
name: "security-ops"
description: "Cross-project baseline security skill. Invoke for security posture, secret hygiene, and hardening checks. Do not invoke for PR functional review or domain feature implementation."
---

# Security Ops

## Когда вызывать
- Нужен baseline security-аудит проекта или подпроекта.
- Требуется проверка secret hygiene и безопасной конфигурации.
- Нужен hardening runbook и контроль минимальных security-практик.

## Когда не вызывать
- Нужен финальный функциональный verdict по PR.
- Требуется реализовать фичу CLI, RAG, VPN или VPS.
- Нужен узкоспециализированный dependency triage в рамках конкретного модуля.

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
- Quick check: `pwsh .\.trae\automation\security_quick_check.ps1`
