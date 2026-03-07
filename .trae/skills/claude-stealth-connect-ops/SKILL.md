---
name: "claude-stealth-connect-ops"
description: "Handles Claude Stealth Connect proxy/VPS automation and diagnostics. Invoke when working on VPS setup, proxy chain config, or operational scripts."
---

# Claude Stealth Connect Ops

## Scope
- Автоматизация и диагностика VPS/Proxy цепочек.
- Скрипты из C:\vault\Projects\Claude Stealth Connect\Assets.
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
- Диагностика VPS: `python "C:\vault\Projects\Claude Stealth Connect\Assets\diagnose_vps.py"`
- Проверка версии XUI: `python "C:\vault\Projects\Claude Stealth Connect\Assets\check_xui_version.py"`
- Проверка IP: `python "C:\vault\Projects\Claude Stealth Connect\Assets\check_vps_ip.py"`
