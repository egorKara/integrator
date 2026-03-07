---
name: "vpn-manager-maintainer"
description: "Maintains vpn-manager configuration, builds, and quality checks. Invoke when working on VPN manager core, configs, or release workflows."
---

# VPN Manager Maintainer

## Routing
- Legacy scope: использовать только для проекта `vpn-manager`.
- Для `vpn-manager-fedora` использовать отдельный skill `vpn-manager-fedora-maintainer`.

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
