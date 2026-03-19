# План выполнения: stealth-nexus + vpn-manager proxy contour

## Цель

Предоставить безопасный и управляемый прокси-контур полного трафика с воспроизводимыми сценариями `apply -> verify -> rollback`, где `stealth-nexus` задаёт архитектуру и эталонные параметры цепочки, а `vpn-manager` реализует операционное управление и автоматическую проверку состояния.

## Допущения

- Контур выполняется на текущем Windows-хосте через `vpn-manager` команды маршрутизации.
- Эталонные параметры цепочки берутся из `stealth-nexus/client_config.json` через `xray-import-stealth`.
- Операции не меняют `Hiddify/tun0`.

## Milestone 1: Синхронизация параметров цепочки

- Задача: импортировать параметры из `stealth-nexus` в `vpn-manager`.
- Команды:
  - `python -m vpn_manager xray-import-stealth`
  - `python -m vpn_manager config show xray`
- Definition of Done:
  - Конфиг `xray` заполнен параметрами цепочки.
  - Команда возвращает успешный код завершения.
- Статус: `[x]`
- Stop-and-fix rule:
  - При ошибке чтения/парсинга `client_config.json` остановить pipeline и исправить путь/формат.

## Milestone 2: Исполнение operational-цикла

- Задача: выполнить `apply -> verify -> rollback`.
- Команды:
  - `python -m vpn_manager route-apply`
  - `python -m vpn_manager route-verify`
  - `python -m vpn_manager route-rollback`
- Definition of Done:
  - `apply` и `rollback` завершены успешно.
  - `verify` создаёт JSON-артефакт с результатами проверок.
- Статус: `[x]`
- Stop-and-fix rule:
  - При неуспехе `apply` или `rollback` остановить выполнение и не продолжать этапы выше.

## Milestone 3: Расширенная проверка и фиксация артефактов

- Задача: выполнить строгий IPv6-профиль и зафиксировать артефакты.
- Команды:
  - `python -m vpn_manager route-verify-ipv6`
  - `pwsh -NoProfile -ExecutionPolicy Bypass -File .\check_quality.ps1`
- Definition of Done:
  - Есть отдельный артефакт строгой верификации.
  - Quality-gate (Ruff/Mypy) проходит.
- Статус: `[x]`
- Stop-and-fix rule:
  - При падении quality-gate исправить код до повторного прогона.
