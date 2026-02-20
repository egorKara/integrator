---
name: "vpn-manager-fedora-maintainer"
description: "Maintains vpn-manager-fedora configuration, builds, and quality checks. Invoke when working on VPN manager core, configs, or release workflows."
---

# VPN Manager Fedora Maintainer

## Scope
- C++ ядро и менеджеры профилей в C:\vault\Projects\vpn-manager-fedora\cpp.
- Конфигурации в C:\vault\Projects\vpn-manager-fedora\config.
- Тесты, линтеры и сборочные проверки.

## Нормальный рабочий цикл
1) Проверить актуальные требования и инструкции в README/INSTALL.
2) Проверить конфиги и валидность параметров.
3) Выполнить проверку качества и сборки.

## Типовые задачи
- Поддержка профилей VPN и автоконнекта.
- Изменение конфигов tor/default.
- Выпускные проверки и отчёты качества.

## Примеры команд
- Проверка качества: `pwsh C:\vault\Projects\vpn-manager-fedora\check_quality.ps1`
