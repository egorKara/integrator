# Asus UX310U Issues Matrix & Remediation — 2026-03-09

## Матрица проблем

| Симптом | Подтверждение | Вероятная причина | Приоритет | Мера устранения | Критерий верификации |
|---|---|---|---|---|---|
| SSH auth нестабилен/`Authentication failed` | `client_chain_apply_20260308_183739.log`, `client_chain_verify_20260308_183739.log` | рассинхрон учётных данных/политика auth | Высокий | привести единую учётку, проверить локальный ssh login на хосте | успешный password-auth и `id -un` |
| Падение цепочки из-за provider auth | `proxy_auth_check_20260308_183825.log`, `us_proxy_chain_double_audit_2026-03-09.md` | невалидная пара login/pass или сессия провайдера | Высокий | reset proxy-сервера у провайдера, перепроверка auth | `AUTH=OK` и успешный apply/verify |
| Флапы сети на Windows NIC (воздействует на доступ к Asus) | `network_adapter_rca_2026-03-08.md`, `nic_stability_hardening_20260309_091109.log` | Realtek power-saving + Wintun churn + DNS timeout | Высокий | держать отключённые EEE/Green/GigaLite/PowerSaving | стабильный линк, `TcpTestSucceeded=True` |
| Повторные freeze на Mint | `mint_freeze_recovery_protocol_2026-03-08.md` | энергопрофиль/драйверный конфликт под нагрузкой | Средний | использовать snapshot+calibrate протокол после инцидента | отсутствие freeze в контрольном окне |
| Конфликт виртуальных адаптеров VPN | `network_adapter_rca_2026-03-08.md` | параллельный lifecycle Wintun | Средний | не запускать параллельные VPN-профили, переинициализация driver stack | исчезновение событий удаления Wintun в инцидентных окнах |

## План мер по приоритетам
1. **Сначала:** закрыть auth-path (SSH + proxy provider auth), без смены паролей в рамках текущего этапа.
2. **Параллельно:** удерживать NIC hardening baseline и мониторить DNS timeout.
3. **Далее:** для Mint применять freeze-protocol при каждом инциденте с обязательной выгрузкой snapshot.

## Базовые артефакты для контроля
- `C:\integrator\reports\nic_stability_hardening_*.log`
- `C:\integrator\reports\proxy_auth_check_*.log`
- `C:\integrator\reports\client_chain_apply_*.log`
- `C:\integrator\reports\client_chain_verify_*.log`
