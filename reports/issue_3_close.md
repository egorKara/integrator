## ✅ Git hygiene: артефакты отделены от продуктовых изменений

Сделано:
- Обновлён `.gitignore`: игнор `reports/gh_issue_memory_*.json`, `reports/perf_baseline_*.json`, `reports/zapovednik_closeout_*.txt`, и любые `.trae/memory/*.md`.
- Локальные артефакты (gh_issue_memory/perf/zapovednik и Trae memory md) удалены из рабочей директории, чтобы не засорять статус.

Текущее состояние:
- В рабочем дереве остались **продуктовые изменения** (код/тесты/доки/CI), которые логично зафиксировать коммитами.
- Полностью “clean” `git status` требует коммитов или отката изменений.

Next step:
- Разложить изменения на тематические коммиты (core/CI/docs/tests) и довести `git status` до clean.
