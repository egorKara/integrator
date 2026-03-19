# US proxy runtime inspection (2026-03-12)

## Тезис
- Основной рабочий контур приложений идёт через Hiddify (`tun0`) и его egress IP `198.22.162.226`, а не через отдельный US SOCKS endpoint `208.214.160.156:50101`.

## Факты
- Hiddify активен, PID `10904`, локальные listener-порты: `127.0.0.1:12334`, `127.0.0.1:12337`, `127.0.0.1:17078`.
- У Hiddify есть множественные исходящие TLS-сессии на `198.22.162.226:443`.
- `api.ipify.org` при обычном direct-пути возвращает `198.22.162.226` (egress через туннель).
- Отдельный proxy endpoint `208.214.160.156:50101` доступен только на порту `50101`; порты `80/443/1080/22` закрыты.
- Протокол endpoint: SOCKS5 (`socks5h` проходит, HTTP proxy на этом порту сбрасывается).
- Гео/ASN proxy endpoint: US, Verizon Business (`AS701`), `ip-api` помечает `proxy=false`, `hosting=false`.
- Системный browser proxy выключен: `ProxyEnable=0`, `WinHTTP=Direct`.
- P0 firewall-блокировки отсутствуют (правила `P0-Block-*` не найдены).

## Проверка сервисов
- YouTube: сетевой доступ есть (`curl` -> 200, HTML и watch-page отдаются).
- OpenAI: стабильно `403` с `cf-mitigated: challenge` (Cloudflare challenge).

## Антитезис
- Гипотеза «ломает локальный firewall/маршрут» не подтверждается.
- Гипотеза «приложения реально ходят через 208.214.160.156:50101» для текущего runtime не подтверждается.

## Синтез
- Наблюдаемая проблема похожа на policy/reputation restriction egress IP туннеля (`198.22.162.226`) и/или app-level anti-proxy behavior, а не на поломку локальной сети.
