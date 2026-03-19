---
name: "vpn-manager-fedora-maintainer"
description: "Maintainer skill for vpn-manager-fedora only. Invoke for vpn-manager-fedora core/config/build/release tasks. Do not invoke for vpn-manager or generic security/PR-only checks."
---

# VPN Manager Fedora Maintainer

## Когда вызывать
- Изменяется код или конфигурация проекта `vpn-manager-fedora`.
- Нужны build/quality/release проверки именно `vpn-manager-fedora`.
- Нужна поддержка профильной логики vpn-manager-fedora.

## Когда не вызывать
- Задача относится к `vpn-manager`.
- Нужен только security baseline без изменений проекта.
- Нужен только pre-merge review без доменной реализации.

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
