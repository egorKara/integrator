---
name: "vpn-manager-maintainer"
description: "Maintainer skill for vpn-manager only. Invoke for vpn-manager core/config/build/release tasks. Do not invoke for vpn-manager-fedora or generic security/PR-only checks."
---

# VPN Manager Maintainer

## Routing
- Legacy scope: использовать только для проекта `vpn-manager`.
- Для `vpn-manager-fedora` использовать отдельный skill `vpn-manager-fedora-maintainer`.

## Когда вызывать
- Изменяется код или конфигурация проекта `vpn-manager`.
- Нужны build/quality/release проверки именно `vpn-manager`.
- Нужна поддержка профильной логики vpn-manager.

## Когда не вызывать
- Задача относится к `vpn-manager-fedora`.
- Нужен только security baseline без изменений проекта.
- Нужен только pre-merge review без доменной реализации.

## Scope
- C++ ядро и менеджеры профилей в `${VAULT_ROOT}\vpn-manager\cpp`.
- Конфигурации в `${VAULT_ROOT}\vpn-manager\config`.
- Тесты, линтеры и сборочные проверки.

## Нормальный рабочий цикл (Verification Loop)
1) **Plan:** Проверить актуальные требования и инструкции в README/INSTALL.
2) **Execute:** Внести изменения в конфиги или код.
3) **Verify:** Выполнить проверку качества и сборки (`check_quality.ps1`).

## Типовые задачи
- Поддержка профилей VPN и автоконнекта.
- Изменение конфигов tor/default.
- Выпускные проверки и отчёты качества.

## Примеры команд
- Проверка качества: `pwsh C:\vault\Projects\vpn-manager\check_quality.ps1`
