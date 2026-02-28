## ✅ Agent Memory: семантика задач (kind=task)

Добавлены рецепты `integrator localai assistant`:
- `task-add --title ... [--prio p0|p1|p2] [--owner ...] [--next-step ...]`
- `tasks-pending` (pending вычисляется как “есть task с `Status: open` и нет event закрытия `TaskId: <id>` + `Status: done`”)
- `task-close --id <task_id> [--notes ...]`

Формат записи:
- task создаётся как `kind=task`, `summary="[TASK] <title>"`, `content` содержит `Status: open`, `Priority: ...`, опционально `Owner/NextStep`.
- закрытие делается append-событием `kind=event` с `content` содержащим `TaskId: <id>` и `Status: done`.

### Проверки
- `python -m unittest tests.test_localai_cli` (OK)
