# US Proxy Workbench (Windows 10 Pro) — 2026-03-09

## Рекомендуемая площадка работ
- Основная площадка: `C:\integrator` на Windows 10 Pro.
- Секреты: `C:\integrator\.env.local` (только локально, без коммита).
- Операционные скрипты:
  - `C:\integrator\set_us_proxy_and_test.ps1`
  - `C:\integrator\network_stability_hardening.ps1`
  - `C:\integrator\vault\Projects\stealth-nexus\Assets\configure_client_proxy.py`

## Почему именно так
- Все актуальные артефакты и логи централизованы в `C:\integrator\reports`.
- Исключается расхождение между ручными командами и automation.
- Упрощается rollback/повторяемость для UX310U -> US Proxy.

## Контур выполнения
1. Обновить `C:\integrator\.env.local` (proxy/client/VPS fallback данные).
2. Прогнать `network_stability_hardening.ps1`.
3. Прогнать `set_us_proxy_and_test.ps1` и проверить внешний IP/страна.
4. Прогнать `configure_client_proxy.py` (apply/verify).
5. Сохранить логи в `C:\integrator\reports` и обновить runbook-статус.
