# P1 Leak Validation (DNS / WebRTC / QUIC) — 2026-03-08 02:35

## Контекст
- Базовый post-check после elevated kill-switch: `C:\integrator\reports\p0_network_check_after_20260308_022745.log`
- Цель: формально подтвердить отсутствие прикладных обходов после закрытия direct egress.

## Проверки и результаты

### 1) DNS leak
- Проверка маршрутов показала отсутствие `0.0.0.0/0` и наличие только split-маршрутов через `wgo0` (`0.0.0.0/1`, `128.0.0.0/1`).
- На Ethernet DNS-сервер остаётся `192.168.31.1`, но активны правила:
  - `P0-Block-DNS-UDP-Ethernet`
  - `P0-Block-DNS-TCP-Ethernet`
  - `P0-Block-All-Ethernet`
- `Resolve-DnsName ifconfig.me` успешен при активном tunnel-контуре.
- Статус: **Pass (DNS обход через Ethernet блокируется firewall + отсутствием default route)**.

### 2) QUIC leak (UDP/443)
- Активно правило `P0-Block-All-Ethernet` (Outbound Block), что блокирует UDP/TCP egress через Ethernet.
- Прикладной QUIC-трафик не может обойти tunnel через Ethernet-интерфейс.
- Статус: **Pass (системный обход QUIC через Ethernet блокирован)**.

### 3) WebRTC leak
- WebRTC использует STUN/UDP и подчиняется системной сетевой политике.
- При активном `P0-Block-All-Ethernet` и отсутствии default route через Ethernet прямой WebRTC egress в обход tunnel невозможен на системном уровне.
- Дополнительно: browser-level fingerprint проверка (`browserleaks`) остаётся рекомендованным визуальным acceptance-чеком.
- Статус: **Pass (системный уровень), Partial (browser-level визуальная валидация не автоматизирована)**.

## P0 контрольные факты
- `SharedAccess` (ICS): `Stopped`.
- `IP Forwarding` для IPv4/IPv6: `Disabled`.
- Firewall P0 правила: активны.
- Статус P0: **Pass** для контура `DNS/IPv6/LAN bypass` в рамках текущей политики kill-switch.

## Артефакты
- `C:\integrator\reports\p0_network_backup_20260308_022745.xml`
- `C:\integrator\reports\p0_killswitch_20260308_022745.log`
- `C:\integrator\reports\p0_network_check_after_20260308_022745.log`
