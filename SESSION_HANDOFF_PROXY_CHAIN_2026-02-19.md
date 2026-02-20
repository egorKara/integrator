## Итоги сессии: Proxy/VPS цепочка и жёсткий режим США

### Контекст и цель
- Цель: любой трафик ноутбука должен идти только через US proxy.
- Режим: только чтение, без применения изменений.
- Узлы: ПК (Windows), ноут (Linux), VPS (NL), Proxy (US).

### Проверенные факты (реальные измерения)
- ПК Windows direct egress: 85.203.40.35.
- Ноут direct egress: 178.66.129.52.
- US proxy egress (ноут): 208.214.160.156.
- VPS SSH: 72.56.96.6:22.
- VPS public IPv6: 2a03:6f02::30c7.
- VPS → US proxy egress тест: 208.214.160.156 (без раскрытия секретов).
- Windows proxy:
  - WinHTTP: прямой доступ (proxy off).
  - WinINET (HKCU): ProxyEnable=0, ProxyServer empty.
  - WinINET (HKLM): ProxyEnable not set.
- Маршруты Windows:
  - wgo0 (WireGuard) up, IPv4 маршруты 0.0.0.0/1 и 128.0.0.0/1 присутствуют.
  - Дефолтный маршрут 0.0.0.0/0 через Ethernet (192.168.31.1) есть.

### Выводы
- Сейчас нет гарантии “весь трафик ноутбука через US”: direct egress у ноута и ПК присутствует.
- Вариант A (ноут → US proxy) подтверждён как технически возможный и предпочтителен.
- Вариант B (ноут → VPS NL → US proxy) также возможен, но сложнее (двойной kill-switch).
- Риск обхода: ПК может стать транзитной точкой к ноуту при внешнем доступе.

### Рекомендованный вариант
- Вариант A: ноут → US proxy (full-tunnel).

### Финальный “железный” план (только чтение)
1) Подготовка: зафиксировать IP/порт/учётку US proxy и тип туннеля (WG/Xray).
2) Включить туннель на ноуте до US proxy.
3) Kill-switch на ноуте: разрешить только loopback и туннель; запретить любой outbound вне туннеля.
4) DNS: только через туннель; блокировать прямой DNS.
5) IPv6: отключить direct IPv6 или обеспечить IPv6 в туннеле.
6) Закрыть обход через ПК: запретить port-forward/маршрутизацию в LAN.
7) Валидация:
   - внешний IP всегда US;
   - при отключении туннеля интернет недоступен;
   - DNS/IPv6 утечек нет.

### Логи и артефакты
- C:\vault\Projects\Claude Stealth Connect\Logs\_probe.json
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_state.json
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_scan_20260218_004459.json
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_artifacts_20260218_194809.json
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_strategy_enable_20260218_195732.json
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_test_20260218_185705.log
- C:\vault\Projects\Claude Stealth Connect\Logs\zapret_now.json

### Команды, которые использовались для фактов
- ifconfig.me/ip (ноут/ПК)
- check_proxy_simple.py (ноут)
- check_vps_ip.py + безопасный egress тест на VPS
- netsh winhttp show proxy + реестр WinINET
- маршруты/интерфейсы Windows (Get-NetRoute/Get-NetIPInterface)
