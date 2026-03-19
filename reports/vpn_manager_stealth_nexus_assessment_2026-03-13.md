# Отчёт: фактическое состояние vpn-manager и интеграция Stealth Nexus

Дата: 2026-03-13  
Исполнитель: Trae Agent (режим исследования)  
Объекты: `C:\integrator\vault\Projects\vpn-manager`, `C:\integrator\vault\Projects\stealth-nexus`

## 1) Методика и границы

- Статус: Проверено  
  Факт подтверждения: выполнены чтения кода/документов и запуск команд в `vpn-manager` (`git status`, `python -m vpn_manager ...`, `check_quality.ps1`).
- Статус: Проверено  
  Факт подтверждения: исследованы интеграционные артефакты Stealth Nexus (`Assets/configure_chain.py`, `Assets/generate_client_config.py`, `client_config.json`).
- Статус: Не проверено  
  Факт подтверждения: реальное VPN-подключение к провайдерам не выполнялось, только CLI/логика MVP и симуляции.

## 2) Фактическое положение дел (матрица)

### 2.1 Состояние репозитория и качество

- Статус: Проверено  
  Факт подтверждения: рабочее дерево сильно изменено — `CHANGED_FILES=540`; ветка `fix/veth-secrets`; последний commit `d159e1601d37fa5eb9223ed4a9ac1a309687b925|2026-02-17 16:13:00 +0300|wip 3: config and cli updates`.
- Статус: Проверено  
  Факт подтверждения: `check_quality.ps1` падает из-за жёстко заданного интерпретатора `c:\LocalAI\assistant\env312\Scripts\python.exe` ([check_quality.ps1](file:///c:/integrator/vault/Projects/vpn-manager/check_quality.ps1#L1-L18)).
- Статус: Противоречиво  
  Факт подтверждения: README сообщает `v0.3 Alpha` и «что не проверено» ([README.md](file:///c:/integrator/vault/Projects/vpn-manager/README.md#L5-L19)); STATUS заявляет `1.0.0 PRODUCTION RELEASE` ([STATUS.md](file:///c:/integrator/vault/Projects/vpn-manager/STATUS.md#L7-L10)).
- Статус: Противоречиво  
  Факт подтверждения: в `pyproject.toml` версия `1.0` ([pyproject.toml](file:///c:/integrator/vault/Projects/vpn-manager/pyproject.toml#L5-L9)); CLI печатает `v1.0 Alpha` ([cli/__init__.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/cli/__init__.py#L167-L183)).

### 2.2 Реальная функциональность ядра

- Статус: Проверено  
  Факт подтверждения: ключевые менеджеры в core — заглушки (`pass`) в [core/vpn_manager.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/core/vpn_manager.py#L20-L59).
- Статус: Проверено  
  Факт подтверждения: `connect` в CLI/провайдерах работает как симуляция (`Connected successfully (simulated)`) в [providers/protonvpn.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/providers/protonvpn.py#L19-L25), [providers/vpngate.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/providers/vpngate.py#L19-L24).
- Статус: Проверено  
  Факт подтверждения: CLI реально исполняется из `src`: `python -m vpn_manager status` и `python -m vpn_manager --help` отрабатывают.
- Статус: Проверено  
  Факт подтверждения: в текущем окружении инструментов нет: `Openvpn=MISSING, Wireguard=MISSING, Nmcli=MISSING, Systemd=MISSING` (вывод `python -m vpn_manager status`).

### 2.3 Конфиги и провайдеры

- Статус: Проверено  
  Факт подтверждения: `config/providers.yaml` содержит `protonvpn`, `vpngate`, `windscribe`, `xray` ([providers.yaml](file:///c:/integrator/vault/Projects/vpn-manager/config/providers.yaml#L1-L13)).
- Статус: Проверено  
  Факт подтверждения: `xray` в конфиге выключен по умолчанию (`enabled: false`) ([providers.yaml](file:///c:/integrator/vault/Projects/vpn-manager/config/providers.yaml#L11-L13)).
- Статус: Проверено  
  Факт подтверждения: Xray-провайдер поддерживает генерацию VLESS-ссылки и валидацию `vless://` ([providers/xray.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/providers/xray.py#L25-L81)).

### 2.4 Тесты

- Статус: Проверено  
  Факт подтверждения: в `tests` найдено `PY_TEST_FILES=106`.
- Статус: Противоречиво  
  Факт подтверждения: документ `STATUS.md` декларирует `468 тестов`, фактическое число test-файлов на диске — 106; численность test-cases не верифицировалась прогоном.
- Статус: Не проверено  
  Факт подтверждения: полный прогон `pytest` не выполнялся, отчёт о pass/fail отсутствует.

## 3) Совместимость со Stealth Nexus (факты)

- Статус: Проверено  
  Факт подтверждения: Stealth Nexus уже работает с Xray/VLESS Reality и генерирует клиентский JSON ([generate_client_config.py](file:///c:/integrator/vault/Projects/stealth-nexus/Assets/generate_client_config.py#L55-L121), [client_config.json](file:///c:/integrator/vault/Projects/stealth-nexus/client_config.json#L1-L77)).
- Статус: Проверено  
  Факт подтверждения: Stealth Nexus умеет формировать цепочку outbound через внешний SOCKS (`PROXY_IP/PROXY_PORT/PROXY_USER/PROXY_PASS`) на серверной стороне ([configure_chain.py](file:///c:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py#L328-L344)).
- Статус: Проверено  
  Факт подтверждения: в `vpn-manager` уже есть `xray` провайдер и `vless` протокол, что даёт прямую основу интеграции ([providers/xray.py](file:///c:/integrator/vault/Projects/vpn-manager/src/vpn_manager/providers/xray.py#L25-L77), [providers.yaml](file:///c:/integrator/vault/Projects/vpn-manager/config/providers.yaml#L11-L13)).
- Статус: Не проверено  
  Факт подтверждения: end-to-end подключение `vpn-manager` -> Stealth Nexus цепочка не запускалось, итоговая маршрутизация хоста не подтверждена.

## 4) Т+А=С

### Тезис

- Перевод интеграции в `vpn-manager` рационален: есть существующий каркас CLI/providers, есть `xray` provider, есть готовые артефакты Stealth Nexus для VLESS/Reality и proxy-chain.
- Текущая блокировка прогресса вызвана не отсутствием идей, а несогласованностью статусов проекта, непроходимым quality-gate и MVP-заглушками в ядре.

### Антитезис (критические вопросы и ответы)

1. Вопрос: Можно ли считать текущий `vpn-manager` production-ready?  
   Статус: Противоречиво  
   Факт подтверждения: `STATUS.md` говорит «готов», `README.md` говорит «alpha/не проверено», core содержит `pass`-заглушки.

2. Вопрос: Есть ли работоспособный quality gate для безопасной интеграции?  
   Статус: Проверено  
   Факт опровержения: `check_quality.ps1` падает на отсутствующем фиксированном python path.

3. Вопрос: Поддерживает ли `vpn-manager` нужный протоколный слой для Stealth Nexus?  
   Статус: Проверено  
   Факт подтверждения: `xray` provider присутствует, `vless://` ссылка генерируется.

4. Вопрос: Подтверждён ли реальный канал трафика через новую интеграцию?  
   Статус: Не проверено  
   Факт опровержения: проведены только симуляционные подключения и чтение кода.

5. Вопрос: Стабилен ли исходный baseline для разработки без потери контекста?  
   Статус: Противоречиво  
   Факт опровержения: 540 локальных изменений делают baseline шумным и рискованным для точной диагностики regressions.

6. Вопрос: Есть ли у нас уже готовая модель chain-конфига из Stealth Nexus для переноса?  
   Статус: Проверено  
   Факт подтверждения: `configure_chain.py` и `generate_client_config.py` содержат конкретные структуры outbound/routing.

7. Вопрос: Можно ли сразу перейти к «весь трафик через прокси» без блокировок?  
   Статус: Не проверено  
   Факт опровержения: в `vpn-manager` нет подтверждённого host-level TUN-path на текущем стенде; перенос логики требует отдельного модуля маршрутизации и верификации.

### Синтез (действия без двусмысленности)

1) **Стабилизация baseline `vpn-manager` перед интеграцией**  
- Команды:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
git status --porcelain > C:\integrator\reports\vpn_manager_git_status_2026-03-13.txt
git rev-parse --abbrev-ref HEAD > C:\integrator\reports\vpn_manager_git_branch_2026-03-13.txt
git log -1 --pretty=format:"%H|%ci|%s" > C:\integrator\reports\vpn_manager_git_head_2026-03-13.txt
```
- Артефакты: три файла отчёта в `C:\integrator\reports\`.
- Откат-команда:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
git reset --hard
git clean -fd
```

2) **Ремонт quality gate**  
- Команды:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
$env:PYTHONPATH="src"
python -m ruff check src
python -m mypy src
```
- Артефакты: stdout/stderr проверок, список ошибок по Ruff/Mypy.
- Откат-команда:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
git checkout -- check_quality.ps1 pyproject.toml mypy.ini ruff.toml
```

3) **Интеграция Stealth Nexus как первого класса провайдера**  
- Действие: включить `xray` в `config/providers.yaml`, добавить загрузку VLESS client-конфига из формата Stealth Nexus (`client_config.json`) в `vpn_manager.providers.xray`.
- Команды:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
$env:PYTHONPATH="src"
python -m vpn_manager config set xray enabled=true protocol=vless
python -m vpn_manager list-providers
python -m vpn_manager list-servers xray
```
- Артефакты: изменённый `config/providers.yaml`, лог CLI.
- Откат-команда:
```powershell
cd C:\integrator\vault\Projects\vpn-manager
git checkout -- config/providers.yaml src/vpn_manager/providers/xray.py src/vpn_manager/cli/__init__.py
```

4) **Верификация «весь трафик перенаправлен» на host-level в рамках vpn-manager**  
- Действие: добавить в `vpn-manager` отдельный runtime-модуль host-routing (TUN mode) по образцу проверенного контура и завести команды `route-apply`, `route-verify`, `route-rollback`.
- Команды верификации:
```powershell
python -m vpn_manager status
python -m vpn_manager connect xray
curl.exe -sS -m 20 https://api.ipify.org?format=json
curl.exe -sS -m 25 -o NUL -w "YT=%{http_code}`n" https://www.youtube.com
curl.exe -sS -m 25 -o NUL -w "GT=%{http_code}`n" https://translate.google.com
```
- Артефакты: журнал проверки egress/IP/HTTP-кодов.
- Откат-команда:
```powershell
python -m vpn_manager disconnect
python -m vpn_manager route-rollback
```

## 5) Финальные рекомендации

1. Зафиксировать единый целевой статус проекта: `alpha` везде до подтверждения реальных подключений и прохода quality-gate.  
2. Перенести Stealth Nexus в `vpn-manager` через `xray` provider как основной путь интеграции.  
3. Ввести host-level модуль маршрутизации в `vpn-manager` и верифицировать egress на уровне ОС, а не только на уровне CLI-подключения.  
4. Убрать жёсткий путь интерпретатора из `check_quality.ps1` и закрепить переносимый запуск через активный python окружения проекта.  
5. Выполнить интеграцию только после очистки или фиксации текущих 540 изменений в отдельный baseline-снимок.
