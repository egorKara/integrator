---
name: "stealth-nexus-ops"
description: "Stealth Nexus operations skill. Invoke for VPS/proxy chain setup, diagnostics, and ops scripts. Do not invoke for CLI refactoring, LocalAI runtime operations, or PR-only reviews."
---

# Stealth Nexus Ops

## Когда вызывать
- Нужна настройка или аудит proxy chain.
- Нужна диагностика VPS и проверка доступности сервисов цепочки.
- Нужны изменения в операционных скриптах проекта Stealth Nexus.

## Когда не вызывать
- Нужен refactor integrator CLI.
- Нужны RAG/SSOT/indexing операции LocalAI assistant.
- Нужен только pre-merge review без выполнения ops-диагностики.

## Scope
- Автоматизация и диагностика VPS/Proxy цепочек.
- Скрипты из C:\integrator\vault\Projects\stealth-nexus\Assets.
- Валидация конфигураций и проверка состояния сервисов.

## Нормальный рабочий цикл
1) Проверить текущие конфиги и параметры подключения.
2) Проверить состояние VPS и сервисов через диагностические скрипты.
3) Применить изменения цепочки и проверить устойчивость.

## Типовые задачи
- Настройка и аудит proxy chain.
- Валидация конфигураций клиент/сервер.
- Сбор артефактов и логов для разборов.

## Примеры команд
- Диагностика VPS: `python "C:\integrator\vault\Projects\stealth-nexus\Assets\diagnose_vps.py"`
- Проверка версии XUI: `python "C:\integrator\vault\Projects\stealth-nexus\Assets\check_xui_version.py"`
- Проверка IP: `python "C:\integrator\vault\Projects\stealth-nexus\Assets\check_vps_ip.py"`
