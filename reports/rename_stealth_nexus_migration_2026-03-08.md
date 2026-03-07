# Миграция имени проекта — 2026-03-08

## Тезис
Переименование выполнено для унификации бренда: `Claude Stealth Connect` → `Stealth Nexus`, папка проекта: `stealth-nexus`.

## Таблица соответствий
| Тип | Было | Стало |
|---|---|---|
| Display name | Claude Stealth Connect | Stealth Nexus |
| Project folder | `C:\integrator\vault\Projects\Claude Stealth Connect` | `C:\integrator\vault\Projects\stealth-nexus` |
| Rules path | `vault/Projects/Claude Stealth Connect/.trae/rules/*` | `vault/Projects/stealth-nexus/.trae/rules/*` |

## Антитезис
- Исторические датированные отчёты в `reports/` не переписывались для сохранения трассируемости.
- Бэкап исходной папки проекта сохранён в `C:\integrator\vault\Projects\_backup_Claude_Stealth_Connect_2026-03-08`.

## Синтез
- Активные конфиги и документация обновлены на новое имя и путь.
- Проверка по старому имени выполнена; остатки сохранены только в исторических артефактах.
