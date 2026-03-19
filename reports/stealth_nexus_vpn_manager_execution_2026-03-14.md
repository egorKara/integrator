# Выполнение связки stealth-nexus + vpn-manager (justdoit)

Дата: 2026-03-14

## Цель

Предоставить безопасный и управляемый прокси-контур полного трафика с воспроизводимыми сценариями `apply -> verify -> rollback`, где `stealth-nexus` задаёт архитектуру и эталонные параметры цепочки, а `vpn-manager` реализует операционное управление и автоматическую проверку состояния.

## Execution-pack

- `C:\integrator\docs\plans.md`
- `C:\integrator\docs\status.md`
- `C:\integrator\docs\test-plan.md`

## Выполненные команды

1. `python -m vpn_manager xray-import-stealth` -> OK
2. `python -m vpn_manager config show xray` -> OK
3. `python -m vpn_manager route-apply` -> OK
4. `python -m vpn_manager route-verify` -> OK
5. `python -m vpn_manager route-verify-ipv6` -> выполнено, строгий профиль не пройден
6. `python -m vpn_manager route-rollback` -> OK
7. `pwsh -NoProfile -ExecutionPolicy Bypass -File .\check_quality.ps1` -> OK

## Артефакты

- Apply: `C:\integrator\reports\system_us_proxy_enable_20260314_070056.log`
- Verify (base): `C:\integrator\vault\Projects\vpn-manager\reports\route_verify_20260314_040113.json`
- Verify (strict IPv6): `C:\integrator\vault\Projects\vpn-manager\reports\route_verify_20260314_040131.json`
- Rollback: `C:\integrator\reports\system_us_proxy_disable_20260314_070131.log`

## Фактический результат

- Базовый профиль верификации: `success=true`
- Egress: `208.214.160.156`
- DNS/HTTP проверки: OK
- Строгий IPv6 профиль: `success=false` (нет рабочего IPv6-канала до endpoint)

## Вывод

- Операционный контур `apply -> verify -> rollback` воспроизводим и работает в базовом профиле.
- Рекомендуемая эксплуатация: базовый профиль как основной gate, строгий IPv6 профиль как отдельный обязательный gate только в IPv6-ready средах.
