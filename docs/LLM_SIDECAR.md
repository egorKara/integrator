# LM Studio Sidecar (артефакты → рекомендации)

## Назначение
- Sidecar — отдельный процесс, который читает артефакты из `reports/` и просит LM Studio сформировать:
  - технические рекомендации,
  - triage падений CI,
  - предложения по тестам.

## Минимальный протокол (вход → выход)
- Вход: набор файлов (обычно JSON/логи) из `reports/`, например:
  - `reports/quality_summary*.json`
  - `reports/*workflow*_summary.json` (или `*.summary.json`)
  - `reports/gitleaks.json`
  - `reports/pip-audit-*.json`
- Выход: Markdown-отчёт в `reports/`:
  - `reports/recommendations_llm_*.md`
  - `reports/ci_triage_llm_*.md`
  - `reports/test_suggestions_llm_*.md`

## Безопасность
- Не передавайте в sidecar:
  - `.env`, секреты, токены;
  - содержимое `vault/`;
  - содержимое `.trae/memory/` и `project_memory.xml`.
- Скрипт по умолчанию блокирует такие пути (можно снять блокировку флагом `--allow-sensitive`, но это не рекомендуется).

## Запуск

### Переменные окружения
- `LMSTUDIO_BASE_URL` (по умолчанию `http://127.0.0.1:1234`)
- `LMSTUDIO_MODEL` (по умолчанию `local-model`)

### Команды
Технические рекомендации:
```powershell
python tools/lm_studio_sidecar.py --mode recommendations --input reports/quality_summary.json --input reports/security_quick_check_*.json
```

Triage CI:
```powershell
python tools/lm_studio_sidecar.py --mode ci-triage --input reports/quality_summary.json --input reports/gitleaks.json --write-response-json
```

Предложения по тестам:
```powershell
python tools/lm_studio_sidecar.py --mode tests --input reports/coverage.xml --input reports/quality_summary.json
```

## Ограничения
- Sidecar не измеряет производительность и не заменяет инструментирование. Он анализирует уже собранные артефакты и формирует рекомендации/планы.
