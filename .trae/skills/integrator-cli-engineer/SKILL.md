---
name: "integrator-cli-engineer"
description: "Maintains the integrator CLI, commands, and tests. Invoke when changing CLI behavior, refactoring output, or running quality checks."
---

# Integrator CLI Engineer

## Scope
- Команды CLI integrator: status/remotes/report/run/doctor/projects.
- Единый формат вывода и устойчивость JSONL.
- Качество: unittest, ruff, mypy.

## Нормальный рабочий цикл
1) Поиск дублирования логики и вынесение в хелперы.
2) Проверка совместимости вывода и сортировки.
3) Обязательные проверки качества после изменений.

## Типовые задачи
- Рефакторинг ядра CLI без смены поведения.
- Улучшение качества вывода и стабильности JSON.
- Добавление команд и параметров с тестами.

## Примеры команд
- Тесты: `python -m unittest discover -s tests -p "test*.py"`
- Ruff: `python -m ruff check .`
- Mypy: `python -m mypy .`
