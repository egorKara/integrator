# Самонастройка (Quality-First)

## Цель
Сделать воспроизводимую кодовую самонастройку для `C:\integrator` и смежных контуров (`LocalAI`, `vault/Projects/*`) с приоритетом качества над скоростью.

## Диалектический принцип (Т+А=С)

### 1) Скорость vs надёжность
- Тезис: быстрые проверки экономят время.
- Антитезис: быстрые проверки пропускают дефекты.
- Синтез: `quality-first` по умолчанию (`full` профиль, строгие guardrails, pre-commit + CI).

### 2) Гибкость ручного запуска vs единый стандарт
- Тезис: вручную можно точнее управлять задачами.
- Антитезис: ручной режим даёт дрейф практик.
- Синтез: единый `scripts/bootstrap_integrator.ps1` + профильные сценарии (`safe`, `full`, `algotrading`).

### 3) Глубокая очистка vs безопасность данных
- Тезис: агрессивная чистка уменьшает шум.
- Антитезис: можно задеть полезные артефакты.
- Синтез: сначала `dry-run`, затем `apply` с логом, только безопасные классы мусора.

## Внедрённые компоненты
- `guardrails.py`: структурные/безопасностные проверки (правила, пути, секреты, рискованные команды, CI integration).
- `ops_checklist.py`: автоматизированный чек-лист с JSON/MD отчётами.
- `scripts/bootstrap_integrator.ps1`: единый bootstrap (profiles, pre-commit install, checklist, quality gates).
- `scripts/profiles/Integrator.Profile.ps1`: профиль PowerShell с алиасами `iboot` и `iprofile`.
- `.pre-commit-config.yaml`: quality-first hooks (`guardrails`, `ruff`, `mypy`, `unittest`) на `pre-commit` и `pre-push`.
- `.github/workflows/ci.yml`: добавлены `pre-commit` quick hooks и strict `guardrails`.

## Рекомендованный запуск
```powershell
Set-Location C:\integrator
.\scripts\bootstrap_integrator.ps1 -Profile full -InstallPreCommit -RunChecklist -RunQuality
```

## Ограничение по «низкоуровневой самонастройке ядра»
Из сессии проекта недоступна настройка внутренних параметров модели/serving-инфраструктуры. Доступ к этому уровню находится на стороне платформы/разработчиков модели.