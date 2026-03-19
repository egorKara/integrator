## Audit Proxy Chain — 2026-02-19

### Контекст
Цель: проверить маршрут трафика от ноутбука до US proxy сервера, выявить утечки/обходы и зафиксировать факты.

### Термины
- Прямой выход: трафик уходит в интернет без локального proxy (WinHTTP/WinINET) и без принудительного туннеля.
- Выход через proxy: трафик направляется через локальный socks/туннель, после чего внешний IP отличается от прямого.
- Клиент: удалённая машина с Xray и локальным socks на 127.0.0.1:1080 (CLIENT_IP из .env).

### Факты (по результатам проверок)
- Ноутбук: публичный IP при прямом обращении к ifconfig.me = 85.203.40.35.
- VPS доступен по SSH: 72.56.96.6:22, TCP ok.
- VPS публичный IP (через SSH): 2a03:6f02::30c7.
- Клиент:
  - CONFIG_OK: /usr/local/etc/xray/config.json существует.
  - 127.0.0.1:1080 LISTEN (tcp/udp).
  - Direct IP клиента: 178.66.129.52.
  - Proxy IP через socks5 127.0.0.1:1080: 208.214.160.156.
- Windows proxy:
  - WinHTTP: прямой доступ (без proxy).
  - WinINET (HKCU): ProxyEnable=0, ProxyServer пуст.
  - WinINET (HKLM): ProxyEnable не задан.
- Маршрутизация Windows:
  - Интерфейс wgo0 (WireGuard) Up, есть маршруты 0.0.0.0/1 и 128.0.0.0/1 (полный охват IPv4).
  - Дефолтный маршрут 0.0.0.0/0 присутствует через Ethernet (192.168.31.1).

### Вывод по маршруту
- На ноутбуке фактически виден IP 85.203.40.35 при прямом запросе, что подтверждает наличие прямого egress.
- На клиенте подтверждается различие direct vs proxy egress (178.66.129.52 → 208.214.160.156), что демонстрирует работу socks-прокси.
- Полная гарантия “любой трафик через proxy” на ноутбуке не подтверждена, так как системный proxy отключён и есть прямой egress.

### Логи (точные пути)
- C:\integrator\vault\Projects\stealth-nexus\Logs\_probe.json
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_state.json
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_scan_20260218_004459.json
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_artifacts_20260218_194809.json
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_strategy_enable_20260218_195732.json
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_test_20260218_185705.log
- C:\integrator\vault\Projects\stealth-nexus\Logs\zapret_now.json

### Риски обхода
- System proxy на ноутбуке отключён, поэтому приложения могут уходить напрямую, минуя proxy.
- Наличие прямого egress IP на ноутбуке подтверждает возможность обхода.

### Рекомендации (без применения изменений)
- Включить системный proxy или обеспечить прозрачный перехват трафика на уровне туннеля.
- Проверить, что маршруты и DNS строго уходят через US proxy/tunnel.
