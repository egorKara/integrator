# Agent Memory: задачи (kind=task)

Цель: хранить задачи для автоматизаций в Agent Memory в append-only стиле, без “редактирования” записей.

## Модель данных

### Task (создание)
- kind: `task`
- summary: `[TASK] <title>`
- content (обязательные строки):
  - `Status: open`
  - `Priority: p0|p1|p2`
- content (опционально):
  - `Owner: <text>`
  - `NextStep: <text>`
- tags (рекомендуемо):
  - `task`
  - `status:open`
  - `prio:p0|p1|p2`

### Close event (закрытие)
- kind: `event`
- summary: `[TASK-CLOSE] <task_id>`
- content (обязательные строки):
  - `TaskId: <task_id>`
  - `Status: done`
- tags (рекомендуемо):
  - `task`
  - `status:done`
  - `task_id:<task_id>`

## CLI (integrator)

Создать задачу:
- `integrator localai assistant task-add --title "..." --prio p1 --owner "..." --next-step "..." --json`

Закрыть задачу:
- `integrator localai assistant task-close --id 123 --notes "..." --json`

Список pending:
- `integrator localai assistant tasks-pending --json`

Pending вычисляется как: “есть task с `Status: open`, и нет close event с `TaskId: <id>` и `Status: done`”.
