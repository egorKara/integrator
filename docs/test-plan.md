# Test Plan: stealth-nexus + vpn-manager contour

## Scope

- Проверка воспроизводимого operational-сценария `apply -> verify -> rollback`.
- Проверка синхронизации эталонных параметров цепочки из `stealth-nexus`.
- Проверка quality-gate кода `vpn-manager`.

## Test Levels

- CLI functional checks
- Integration checks (proxy contour)
- Quality checks (Ruff/Mypy)

## Critical Cases

- Импорт `xray` параметров из `stealth-nexus` проходит без ошибок.
- `route-apply` устанавливает контур и пишет артефакт.
- `route-verify` возвращает валидный JSON отчёт.
- `route-rollback` гарантированно откатывает контур.
- `route-verify-ipv6` корректно отражает строгий IPv6-статус.

## Acceptance Gates

- Gate A: `xray-import-stealth` завершён успешно.
- Gate B: `route-apply` и `route-rollback` успешны.
- Gate C: `route-verify` формирует отчёт с `success=true` для базового профиля.
- Gate D: quality-check проходит без ошибок.

## Commands

- `python -m vpn_manager xray-import-stealth`
- `python -m vpn_manager config show xray`
- `python -m vpn_manager route-apply`
- `python -m vpn_manager route-verify`
- `python -m vpn_manager route-verify-ipv6`
- `python -m vpn_manager route-rollback`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File .\check_quality.ps1`
