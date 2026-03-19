---
name: justdoit
description: "Default execution-planning skill for almost any non-trivial repo task. Turns a raw task, feature request, PRD, or project brief into durable execution docs: `plans.md`, `status.md`, and `test-plan.md` (or existing repo equivalents), then proposes execution before starting. Use by default unless the user clearly wants a trivial one-shot answer, pure discussion, or no planning."
---

# justdoit

Convert a task into a short execution analysis plus three durable repo files: a plan file that acts as the source of truth, a status file that acts as the live execution log, and a test plan that defines the validation and release gates.

Use the same core ideas as the PRD prompt pack: dependency-safe milestones, validation-first execution, repair-before-continue, resumability, explicit assumptions, and a clean handoff into the next execution run.

## Invocation Policy

- Treat `justdoit` as the default mode for almost any non-trivial task in a repo.
- Use it for product work, coding work, PRD decomposition, repo changes, or execution planning unless the task is obviously tiny.
- Skip it only when the user clearly wants:
  - a one-line factual answer;
  - pure brainstorming or discussion with no execution pack;
  - a trivial edit that does not benefit from planning.
- If in doubt, prefer using `justdoit`.
