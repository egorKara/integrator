# Win10 Proxy Priority Execution — 2026-03-09

## Исходные вводные
- Ноутбук (SSH/auth) переведён на паузу.
- Приоритет: Windows 10 Pro прокси-контур.
- Данные из `.env.local` нормализованы и структурированы.

## Что сделано
1. `.env.local` приведён к машиночитаемому виду с отдельными полями:
   - `PROXY_IP`, `PROXY_PORT`, `PROXY_SOCKS_PORT`, `PROXY_USER`, `PROXY_PASS`
   - `PROXY_PROTOCOL`, `PROXYSELLER_API_KEY`, `PROXYSELLER_API_IP`, `PROXYSELLER_DOCS_URL`
2. Активный контур выставлен на SOCKS:
   - `PROXY_PROTOCOL=socks5h`
   - `PROXY_PORT=50101`
3. `set_us_proxy_and_test.ps1` доработан:
   - поддержка `-ProxyProtocol` (`http`/`socks5h`);
   - корректная логика skip для WinHTTP при SOCKS;
   - верификация через `curl` (работает и для HTTP, и для SOCKS).
4. Выполнен matrix-тест HTTP/SOCKS:
   - HTTP `:50100` — timeout;
   - SOCKS `:50101` — success.

## Подтверждающие артефакты
- `C:\integrator\reports\proxy_win10_matrix_20260309_094453.log`
- `C:\integrator\reports\us_proxy_apply_20260309_094726.log`

## Факт результата
- Win10 прокси-контур работоспособен на `socks5h://208.214.160.156:50101`.
- Подтверждён US egress:
  - IP `208.214.160.156`
  - Country `US`
  - Region `Virginia`
  - Timezone `America/New_York`

## По API ключу
- API ключ сохранён в `.env.local` и может использоваться для операций управления у провайдера (order/auth/list) через их API.
- Для рабочего прокси-трафика API ключ не обязателен: текущий рабочий путь — login/password прокси.

## Операционный baseline (Win10)
1. Заполненный `.env.local` — единственный источник секретов.
2. Для проверки/применения использовать `set_us_proxy_and_test.ps1` с `socks5h`.
3. Все подтверждения сохранять в `C:\integrator\reports`.
