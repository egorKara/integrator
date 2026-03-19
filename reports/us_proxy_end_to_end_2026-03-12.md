# US Proxy: путь от начала до конца (2026-03-12)

## Контекст
- Цель: безопасно восстановить и стабилизировать US-proxy без потери интернета, затем вынести маршрут прокси в независимый host-route через Ethernet.
- Контур: Windows 10, локальный интерфейс Ethernet, дополнительный tunnel-интерфейс tun0 (Hiddify).

## Тезис
- Контур US-proxy восстановлен, многократно верифицирован, затем вынесен в независимый host-route через Ethernet.
- Добавлена автоматизация операций маршрута и rollback.

## Хронология

### 1) Безопасное восстановление контура
- Проверено: первичный диагностический срез после старта задачи — [p0_network_check_after_20260312_042152.log](file:///C:/integrator/reports/p0_network_check_after_20260312_042152.log).
- Проверено: первичный backup сети — `p0_network_backup_20260312_042202.xml`.
- Проверено: первая попытка pipeline стартовала, но была неполной (без END) — [win10_proxy_pipeline_20260312_042246.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_042246.log).
- Проверено: после восстановления рабочего `.env.local` pipeline завершился успешно — [win10_proxy_pipeline_20260312_042613.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_042613.log).

### 2) Стабильные повторы цикла backup -> pipeline -> collect
- Проверено: успешные прогоны pipeline:
  - [win10_proxy_pipeline_20260312_043032.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_043032.log)
  - [win10_proxy_pipeline_20260312_043537.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_043537.log)
  - [win10_proxy_pipeline_20260312_045800.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_045800.log)
  - [win10_proxy_pipeline_20260312_052855.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_052855.log)
- Проверено: каждый прогон формировал тройку артефактов:
  - backup XML: `p0_network_backup_20260312_*.xml`
  - pipeline log: `win10_proxy_pipeline_20260312_*.log`
  - post-check log: `p0_network_check_after_20260312_*.log`

### 3) Подтверждение US-выхода
- Проверено: US-гео и IP прокси подтверждены по apply-логам:
  - [us_proxy_apply_20260312_042644.log](file:///C:/integrator/reports/us_proxy_apply_20260312_042644.log)
  - [us_proxy_apply_20260312_043103.log](file:///C:/integrator/reports/us_proxy_apply_20260312_043103.log)
  - [us_proxy_apply_20260312_043608.log](file:///C:/integrator/reports/us_proxy_apply_20260312_043608.log)
  - [us_proxy_apply_20260312_045831.log](file:///C:/integrator/reports/us_proxy_apply_20260312_045831.log)
  - [us_proxy_apply_20260312_052926.log](file:///C:/integrator/reports/us_proxy_apply_20260312_052926.log)

### 4) Нормализация секретов и конфигурации
- Проверено: `.env.local` оставлен только с несекретными полями `PROXY_IP/PROXY_PORT/PROXY_USER/PROXY_PROTOCOL/PROXY_CRED_TARGET` — [.env.local](file:///C:/integrator/.env.local).
- Проверено: пароль остаётся только в Credential Manager (pipeline валидирует credential lookup в рантайме) — [run_win10_proxy_pipeline.ps1](file:///C:/integrator/run_win10_proxy_pipeline.ps1).

### 5) Перенаправление через Ethernet и независимый маршрут
- Проверено: был создан host-route `208.214.160.156/32` через Ethernet (ifIndex 7, gateway 192.168.31.1, metric 1).
- Проверено: после создания host-route выбор маршрута к proxy IP идёт через Ethernet даже при активном Hiddify.
- Проверено: host-route не persistent по умолчанию (`Persistent Routes: None`), то есть независим от глобальной таблицы до явного `-p`.
- Не проверено: поведение маршрута после перезагрузки без `-p` в данном цикле.

### 6) Автоматизация рекомендаций
- Проверено: добавлен скрипт автоматизации [automate_us_proxy_route.ps1](file:///C:/integrator/automate_us_proxy_route.ps1) с действиями:
  - `VerifyRoute`
  - `EnsureEthernetHostRoute`
  - `DeleteHostRoute`
  - `RollbackLatest`
- Проверено: rollback берётся из `BACKUP_DIR` последнего `win10_proxy_pipeline_*.log` и выполняется через [restore_win10_inet_access.ps1](file:///C:/integrator/restore_win10_inet_access.ps1).

## Антитезис (риски и факты)
- Риск: потеря доступа при неправильной маршрутизации.
  - Факт-подтверждение: риск снижен обязательным pre-backup (`p0_network_backup_*.xml`) и командой rollback из последнего pipeline-лога.
- Риск: зависимость от tun0/Hiddify для пути до proxy IP.
  - Факт-опровержение: после создания host-route маршрут к proxy IP идёт через Ethernet.
- Риск: хранение секрета в файле.
  - Факт-опровержение: секрет вынесен в Credential Manager, `.env.local` содержит только несекретные поля.

## Синтез (рабочий стандарт)
1. `pwsh -File C:\integrator\.trae\automation\p0_network_backup.ps1`
2. `pwsh -ExecutionPolicy Bypass -File C:\integrator\run_win10_proxy_pipeline.ps1`
3. `pwsh -File C:\integrator\.trae\automation\p0_network_collect.ps1`
4. `pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\automate_us_proxy_route.ps1 -Action VerifyRoute`
5. При аварии: `pwsh -NoProfile -ExecutionPolicy Bypass -File C:\integrator\automate_us_proxy_route.ps1 -Action RollbackLatest`

## Финальный статус
- Проверено: US-proxy рабочий, верификация `VERIFY_PROXY_STATUS=OK` в последнем прогоне — [win10_proxy_pipeline_20260312_052855.log](file:///C:/integrator/reports/win10_proxy_pipeline_20260312_052855.log).
- Проверено: документированный путь от восстановления до автоматизации завершён.
