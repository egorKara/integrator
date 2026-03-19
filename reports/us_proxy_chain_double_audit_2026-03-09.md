# US Proxy Chain Double Audit — 2026-03-09

## 1) Проверка прошлой цепочки (Asus UX310U -> VPS -> US proxy)

### Подтверждено по артефактам
- Целевая архитектура и runbook для многохоп-цепочки зафиксированы в KB.
- В operational-логах был временный сдвиг на схему `notebook -> US proxy` без VPS.
- Host-side hardening/guardrails и leak-check ранее закрывались.

### Текущие блокеры (по последним логам)
- SSH в ноутбук не стабилен по auth (`Authentication failed`) на этапе client apply/verify.
- Provider/proxy auth не проходит (`AUTH=FAIL`).
- Из-за двух пунктов выше end-to-end DoD цепочки не закрыт.

### Вывод
- Проблема не только в прокси-конфиге: одновременно есть блокер в SSH-auth до ноутбука и блокер в proxy auth у провайдера.
- Плановая корректная операция: reset proxy-сервера у провайдера (не reset VPS) после фикса credential-path.

## 2) Повторная проверка с учётом vpn-manager-fedora

### Что найдено
- Отдельный актуальный репозиторий `vpn-manager-fedora` не обнаружен в рабочем дереве; активен `vpn-manager` (Fedora-тег в реестре).
- В `vpn-manager` есть базовая Linux VPN/diag логика, но нет готового end-to-end сценария US proxy через VPS уровня `configure/deploy/cutover`.
- Практические скрипты цепочки находятся в `stealth-nexus/Assets`.

### Вывод
- Ничего критичного не упущено по месту хранения сценариев: рабочие automation-скрипты действительно в `stealth-nexus`, не в `vpn-manager`.

## 3) Повторный запуск network_stability_hardening

### Запуск
- Выполнен повторный старт `C:\integrator\network_stability_hardening.ps1` с UAC relaunch.

### Новый лог
- `C:\integrator\reports\nic_stability_hardening_20260309_091109.log`

### Верификация ключей
- Подтверждено:
  - `*EEE = Выкл`
  - `EnableGreenEthernet = Выкл`
  - `GigaLite = Выкл`
  - `PowerSavingMode = Выкл`
  - `AutoDisableGigabit = Выкл`
- `TcpTestSucceeded=True` до `192.168.31.124:22`.

## 4) Финальный шаг закрепления

1. Зафиксировать текущий профиль NIC как эталон:
   - сохранить лог `nic_stability_hardening_20260309_091109.log` как baseline.
2. Исключить churn виртуальных VPN-адаптеров:
   - не запускать одновременно несколько VPN-клиентов/профилей.
3. После этого повторить только credential-path:
   - валидный SSH auth на ноутбук;
   - валидный US proxy auth;
   - затем client apply/verify.

## 5) Файлы для безопасного ввода секретов
- `C:\integrator\.env.local.template`
- `C:\integrator\.env.local`
