## ✅ CLI: команды чтения agent memory

Добавлены рецепты `integrator localai assistant`:
- `memory-search --q ...`
- `memory-recent`
- `memory-retrieve`
- `memory-stats`
- `memory-feedback --id ... --rating ...`

JSON-вывод реализован как JSONL: одна запись на строку; токены не выводятся.

### Проверки
- `python -m unittest tests.test_localai_cli` (OK)
