## Update: подпроект вынесен из дерева integrator

- Сделано:
  - `bhagavad-gita-reprint/` перемещён из `C:\integrator\` во внешний путь `C:\bhagavad-gita-reprint\`.
  - В `C:\integrator` конфликтных маркеров (`<<<<<<<`/`=======`/`>>>>>>>`) больше нет.
  - Проверено, что `integrator` не зависит от подпроекта: `python -m integrator doctor`, `ruff`, `mypy`, `unittest` проходят.

- Осталось:
  - Ничего по scope этой задачи.

- Верификация:
  - `python -m integrator doctor` → ok
  - `python -m ruff check .` → ok
  - `python -m mypy .` → ok
  - `python -m unittest discover -s tests -p "test*.py"` → ok
  - Поиск конфликтных маркеров в `C:\integrator` → нет совпадений

- Next atomic step:
  - Если потребуется работа с `bhagavad-gita-reprint`, добавить его как отдельный root вне репозитория и управлять через env (`INTEGRATOR_ROOTS`).
