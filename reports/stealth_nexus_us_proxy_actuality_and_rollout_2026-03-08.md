# Stealth Nexus: актуальность базы и план развёртывания US Proxy (Linux Mint 22.1)

Дата: 2026-03-08  
Область: `C:\integrator\vault\Projects\stealth-nexus`, `C:\integrator\reports`, governance-файлы `.trae/*`.

## 1) Инвентаризация источников с A/B/C и обоснованием

| База | Источник | Тема | Дата/срез | A/B/C | Обоснование | Статус проверки |
|---|---|---|---|---|---|---|
| KB | [Runbook-P0-Network-After-Admin.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Runbook-P0-Network-After-Admin.md) | Применённые сетевые меры и остаточные риски | 2026-02-20 | A | Используется как операционный baseline и связан с P0 задачами | Проверено |
| KB | [Runbook-P0-Network-Checks.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Runbook-P0-Network-Checks.md) | Диагностика маршрутов/DNS/IPv6 | 2026-02-20 | A | Непосредственно используется для preflight/post-check | Проверено |
| KB | [Hardware-Setup-UX310U.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Hardware-Setup-UX310U.md) | Mint 22.1, anti-freeze, power profile | 2026-02-19 | A | Прямо покрывает аппаратный профиль и стабилизацию | Проверено |
| KB | [Tasks.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Tasks.md) | Открытый backlog P0/P1/P2 | 2026-02-20 | A | Явный список незакрытых задач и долгов | Проверено |
| Assets | [configure_chain.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py), [deploy_client.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/deploy_client.py), [configure_client_proxy.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_client_proxy.py) | Автоматизация VPS/клиента/проверок egress | актуальное состояние файлов | A | Исполняемые скрипты реализации rollout | Проверено |
| reports | [AUDIT_PROXY_CHAIN_2026-02-19.md](file:///C:/integrator/AUDIT_PROXY_CHAIN_2026-02-19.md) | Фактический аудит direct/proxy egress | 2026-02-19 | A | Подтверждающий артефакт для состояния маршрутизации | Проверено |
| KB | [Architecture-ProxyChain.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Architecture-ProxyChain.md) | Архитектура цепочки | без lifecycle-поля | B | Содержательно релевантно, но метаданные неполные | Проверено |
| KB | [Compatibility-Study-2026-02-19.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Compatibility-Study-2026-02-19.md) | Совместимость Mint/UX310UAR | 2026-02-19 | B | Аналитический документ, не оперативный runbook | Проверено |
| Logs* | [laptop_reboot_logs_20260220_024349.log](file:///C:/integrator/reports/laptop_reboot_logs_20260220_024349.log) | Факты reboot/hang | 2026-02-20 | B | Лог подтверждает инциденты, используется как evidence | Проверено |
| governance | [project_rules.md](file:///C:/integrator/.trae/rules/project_rules.md), [user_rules.md](file:///C:/integrator/.trae/rules/user_rules.md), [AGENTS.md](file:///C:/integrator/AGENTS.md) | Ограничения и process-контур | актуальное состояние файлов | B | Нормативные источники для способа выполнения rollout | Проверено |
| Notes | [Working-Draft.md](file:///C:/integrator/vault/Projects/stealth-nexus/Notes/Working-Draft.md), [Session-Handoff-20260218_2350.md](file:///C:/integrator/vault/Projects/stealth-nexus/Notes/Session-Handoff-20260218_2350.md) | Рабочие гипотезы/hand-off | 2026-02-18 | B | Полезный контекст, но не итоговые решения | Проверено |
| Logs* (архив) | `Logs.bak.*` в `vault/Projects/stealth-nexus` | Исторические снапшоты zapret/scan | 2026-02 | C | Архив, не источник текущих решений | Проверено |
| Notes (legacy) | [Legacy_Mint_Guide.md](file:///C:/integrator/vault/Projects/stealth-nexus/Notes/Legacy_Mint_Guide.md), [Legacy_Status_2025.md](file:///C:/integrator/vault/Projects/stealth-nexus/Notes/Legacy_Status_2025.md) | Исторический контекст | 2025 | C | Устаревшие предпосылки и планирование | Проверено |

## 2) Матрица трассируемости «Требование -> Источник -> Реализация -> Статус»

| Требование spec | Источник | Реализация/факт | Статус |
|---|---|---|---|
| Полный аудит актуальности источников (A/B/C) | Раздел 1 этого отчёта + [project_rules.md](file:///C:/integrator/.trae/rules/project_rules.md) | Источники собраны по KB/Notes/Assets/Logs*/reports/governance и классифицированы | Реализовано |
| Матрица «Реализовано/Частично/В плане/Риск-долг» | [Tasks.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Tasks.md), [AUDIT_PROXY_CHAIN_2026-02-19.md](file:///C:/integrator/AUDIT_PROXY_CHAIN_2026-02-19.md), раздел 3 | Зафиксирована единая таблица статусов и доказательства по каждому пункту | Реализовано |
| Incident-gated стабилизация ноутбука | [Self-Analysis-2026-02-19-Freeze.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Self-Analysis-2026-02-19-Freeze.md), [Runbook-P0-Network-Checks.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Runbook-P0-Network-Checks.md), раздел 4 | Формализовано правило запуска стабилизации только при подтверждённом инциденте | Реализовано |
| Детальный rollout-runbook US Proxy | Скрипты [configure_chain.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py), [deploy_client.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/deploy_client.py), `.trae/automation/*`, раздел 5 | Покрыты фазы preflight, VPS, client, hardening, leak-check, эксплуатация и rollback | Реализовано |
| Условность фазы стабилизации (MODIFIED) | Раздел 4 этого отчёта | Стабилизация исключена из штатного обязательного потока | Реализовано |
| Запрет обязательной стабилизации в штатном потоке (REMOVED) | Раздел 4 этого отчёта | Обязательная стабилизация заменена на мониторинг baseline | Реализовано |

## 3) Реализовано / Частично / В плане / Риск-долг

### Реализовано
1. Автоматизация VPS proxy-chain: [configure_chain.py:L264-L325](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py#L264-L325).  
2. Автоматизация клиентского Xray rollout: [deploy_client.py:L68-L118](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/deploy_client.py#L68-L118).  
3. Проверка direct/proxy egress на клиенте: [configure_client_proxy.py:L93-L128](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_client_proxy.py#L93-L128).  
4. P0 firewall/IPv6 меры с админ-правами: [Runbook-P0-Network-After-Admin.md:L14-L17](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Runbook-P0-Network-After-Admin.md#L14-L17).  

### Частично
1. Kill-switch: остаётся дефолтный route через Ethernet: [Runbook-P0-Network-After-Admin.md:L20-L25](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Runbook-P0-Network-After-Admin.md#L20-L25).  
2. Browser leak-check: отсутствует полный автоматизированный контур WebRTC/QUIC.  

### В плане
1. DNS-only-via-tunnel, LAN bypass hardening, leak validation, TLS policy: [Tasks.md:L12-L16](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Tasks.md#L12-L16).  
2. Контрольный период стабильности после freeze-инцидентов: [Self-Analysis-2026-02-19-Freeze.md:L35-L40](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Self-Analysis-2026-02-19-Freeze.md#L35-L40).  

### Риск/долг
1. В automation панели используется `verify=False`: [configure_chain.py:L80-L84](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py#L80-L84), [configure_chain.py:L336-L357](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_chain.py#L336-L357).  

## 4) Incident-gated правило стабилизации ноутбука

- Штатный режим: применяется только мониторинг baseline без конфигурационных изменений.  
- Триггеры стабилизации: подтверждённые `freeze/hang/reboot/network degradation` с логами.  
- Обязательные артефакты перед изменениями: системные логи, сетевой preflight, фиксация текущего профиля питания.  
- Критерий возврата в штатный режим: контрольное окно без повторных инцидентов.

## 5) Детальный runbook развёртывания US Proxy (Mint 22.1)

### Фаза 0 — Preflight и freeze-baseline
1. Снять baseline ноутбука: kernel, iwlwifi, i915, thermald, tlp, power policy.
2. Проверить отсутствие TUN-конфликтов (WARP отключён в рабочем профиле).
3. Проверить журналы на hang/reboot и зафиксировать baseline-артефакт.
4. Переход: система стабильна под нагрузкой.

### Фаза 1 — Подготовка US Proxy и VPS
1. Проверить SSH доступность ноутбука UX310U для automation apply/verify.
2. Подтвердить US Residential SOCKS5 параметры без хранения секретов в git.
3. Зафиксировать целевую схему `UX310U -> US Residential -> Target`.
4. При auth-деградации провайдера выполнять reset proxy-сервера (не VPS).
5. Переход: валидный доступ к прокси и рабочий SSH auth до UX310U.

### Фаза 2 — Настройка цепочки на VPS
1. В штатном режиме пропускается (VPS в резервном контуре).
2. Используется только при fallback-инциденте.
3. Переход: n/a для official потока.

### Фаза 3 — Настройка клиента на ноутбуке
1. Обновить `client_config.json`, развернуть через [deploy_client.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/deploy_client.py).
2. Применить system/desktop proxy и сделать direct/proxy IP проверку через [configure_client_proxy.py](file:///C:/integrator/vault/Projects/stealth-nexus/Assets/configure_client_proxy.py).
3. Включить guardrails: kill-switch, DNS через tunnel/proxy, ограничение IPv6 вне туннеля.
4. Переход: штатный трафик идёт через proxy-контур без тихого direct fallback.

### Фаза 4 — Hardening на Windows-узле (при участии в цепочке)
1. Применить [p0_network_apply.ps1](file:///C:/integrator/.trae/automation/p0_network_apply.ps1) и [p0_network_killswitch.ps1](file:///C:/integrator/.trae/automation/p0_network_killswitch.ps1).
2. Собрать post-check через [p0_network_collect.ps1](file:///C:/integrator/.trae/automation/p0_network_collect.ps1).
3. Проверить route policy, DNS leakage, IPv6 bypass, forwarding/ICS.
4. Переход: P0 риски закрыты.

### Фаза 5 — Leak-check и приёмка
1. Проверить direct/proxy egress и гео US residential.
2. Выполнить DNS/WebRTC/QUIC leak-check (browser + CLI).
3. Проверить целевые сервисы на отсутствие блокировок/деградации.
4. Приёмка: стабильный US egress, нет DNS/WebRTC/QUIC утечек, нет повторяющихся freeze/hard reboot.

### Фаза 6 — Эксплуатация и rollback
1. Зафиксировать daily quick-check и weekly deep-check.
2. Проводить ротацию proxy credentials и SLA-контроль.
3. Готовый rollback: [p0_network_rollback.ps1](file:///C:/integrator/.trae/automation/p0_network_rollback.ps1) + fallback-профиль без потери удалённого доступа.

## 6) Валидация полноты и непротиворечивости

| Проверка | Результат | Подтверждение |
|---|---|---|
| Покрытие баз KB/Notes/Assets/Logs*/reports/governance | Пройдено | Раздел 1, инвентаризационная таблица |
| Покрытие тем US proxy / Mint 22.1 / зависания / питание | Пройдено | [Proxy-Config.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Proxy-Config.md), [Hardware-Setup-UX310U.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Hardware-Setup-UX310U.md), [Self-Analysis-2026-02-19-Freeze.md](file:///C:/integrator/vault/Projects/stealth-nexus/KB/Self-Analysis-2026-02-19-Freeze.md) |
| Матрицы и runbook согласованы между собой | Пройдено | Разделы 2, 3, 5 используют единые статусы и критерии перехода |
| Выводы опираются на проверяемые артефакты | Пройдено | Табличные ссылки на файлы/логи/скрипты |

## 7) Текущие приоритеты

1. Закрыть остаточный direct egress через дефолтный Ethernet route.
2. Убрать `verify=False` и закрепить strict TLS-политику.
3. Закрепить полный DNS/WebRTC/QUIC leak-check как обязательный acceptance gate.
