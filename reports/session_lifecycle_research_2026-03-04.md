# Исследование жизненного цикла сессии и критериев закрытия (2026-03-04)

## Цель
- Зафиксировать рекомендации по append-first циклу.
- Определить, какие параметры реально меняются в одной сессии.
- Определить, как обнаруживать изменения и когда автоматически закрывать сессию.

## Зафиксированные рекомендации
- Канон работы: append-first (`workflow zapovednik append` без `--path`).
- После `workflow zapovednik finalize` следующий `append` без `--path` автоматически открывает новую сессию.
- `session open --json` сохраняется как fallback для ручного принудительного старта и диагностики.

## Что меняется в рамках одной сессии (факт по коду)

| Параметр | Где меняется | Как обнаружить | Для закрытия |
|---|---|---|---|
| `zapovednik_current.txt` (текущий указатель) | `start_session`, `finalize_session` | читать `.trae/memory/zapovednik_current.txt` | косвенно: пустой указатель после finalize означает завершение цикла |
| Имя и путь файла сессии | `start_session` (`YYYY-MM-DD-HHMM[-NN]`) | `Path.exists()` + сравнение пути | полезно для ротации и аудита |
| Кол-во сообщений (`messages_total`) | `finalize_session -> _compute_stats` | парсить блок `## Итоги и статистика` | прямой триггер при превышении лимита |
| Кол-во `?` (`question_marks`) | `_compute_stats` | парсить итоговый блок | слабый сигнал сложности/неопределённости |
| Частотные токены (`top_tokens`, `repeats`) | `_compute_stats` | парсить итоговый блок | сигнал зацикливания/повторов |
| Флаг `session_closed: true` | `_format_stats` | искать строку в итоговом блоке | бинарный факт закрытия |
| `meta.ts`, `meta.role`, `meta.cwd` каждого сообщения | `append_message` | парсить блоки `### msg` | использовать для темпа/длительности/контекста |
| `path_masked`, `success` (только `session open`) | `_cmd_zapovednik_start` | JSON-ответ CLI | служебный fallback-контракт |

Файлы-источники:
- `zapovednik.py`: [zapovednik.py](file:///c:/integrator/zapovednik.py)
- `cli_workflow.py`: [cli_workflow.py](file:///c:/integrator/cli_workflow.py)
- Тесты сценариев: [test_zapovednik.py](file:///c:/integrator/tests/test_zapovednik.py)

## Какие сигналы уже есть в репозитории, но не в Zapovednik-решении
- Quality-сигналы (`ruff/mypy/unittest/coverage`) в `quality_summary`.
- Perf-сигналы (`min/median/p95/max`, `any_failed`) в `perf_baseline`.
- Консистентность артефактов закрытия сессии: `tools/check_session_close_consistency.py`.

Вывод: инфраструктурные сигналы есть, но для решения «пора закрывать именно текущую диалоговую сессию» не хватает runtime-порогов по контексту/размеру самой сессии.

## Внешние источники и подтверждённые выводы
- Поиск перезапущен с актуальной датой (2026) и пересмотром выдачи.
- В итог включены только источники с высокой надёжностью (официальная документация/peer-reviewed публикации); агрегаторы и личные блоги использованы только как вторичный фон и не влияют на выводы.
- Anthropic (Context Engineering): контекст — ограниченный ресурс, есть деградация полезности при росте объёма; рекомендованы compaction, note-taking, подагенты.
  - Источник: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- ACL/TACL Lost in the Middle: качество извлечения данных из середины длинного контекста деградирует.
  - Источник: https://aclanthology.org/2024.tacl-1.9/
- OpenAI Help: usage доступен в ответе API (`prompt_tokens`, `completion_tokens`, `total_tokens`), включая streaming (`include_usage`).
  - Источник: https://help.openai.com/en/articles/6614209-how-do-i-check-my-token-usage
- OpenAI Help: различие prompt/completion токенов и ограничения по входу/выходу.
  - Источник: https://help.openai.com/en/articles/7127987-what-is-the-difference-between-prompt-tokens-and-completion-tokens
- Microsoft Semantic Kernel: практики reduction (truncation/summarization/token-based), reducers с target/threshold.
  - Источник: https://learn.microsoft.com/en-us/semantic-kernel/concepts/ai-services/chat-completion/chat-history

## Практическая модель “когда закрывать сессию” (предложение)

### Базовые пороги (v1)
- `messages_total >= 40` -> мягкий сигнал закрытия.
- размер markdown-файла сессии `>= 180 KB` -> мягкий сигнал закрытия.
- оценка токенов истории `>= 70%` от лимита текущей модели -> мягкий сигнал закрытия.
- `>= 85%` от лимита -> жёсткий сигнал закрытия (обязательно finalize + compaction-note).
- `repeats` содержит >= 5 токенов с частотой >= 3 и нет нового результата за последние 8 сообщений -> сигнал зацикливания, рекомендовать закрытие.

### Оценка токенов без привязки к провайдеру
- Быстрая эвристика: `approx_tokens = ceil(chars / 4)` для RU/EN mixed текста.
- Предпочтительно: если доступен usage API, использовать фактический `prompt_tokens/total_tokens`.

### Decision score (v1)
- `close_score = size_ratio*0.35 + token_ratio*0.4 + repetition_ratio*0.15 + latency_degradation*0.1`
- Автозакрытие рекомендовать при `close_score >= 0.75` или любом жёстком сигнале.

## Как обнаруживать сигналы автоматически
1. Читать текущий путь из `zapovednik_current.txt`.
2. Считать:
   - `file_size_bytes`,
   - количество блоков `### msg`,
   - оценку токенов по эвристике или API usage.
3. Проверять повторяемость:
   - использовать существующие `top_tokens/repeats` из `finalize`-модели,
   - либо оперативно считать частоты по последним N сообщениям.
4. Решение:
   - при срабатывании порогов выдать предупреждение перед `append`,
   - при жёстком сигнале предложить/выполнить `finalize`.

## Что стоит внедрить в integrator следующим шагом
- Команда `workflow zapovednik health --json`:
  - `messages_total`, `file_size_bytes`, `approx_tokens`, `token_ratio`, `close_score`, `recommend_close`.
- Необязательный флаг в `append`: `--auto-finalize-on-threshold`.
- Документировать модель порогов в `docs/SESSION_CLOSE_PROTOCOL.md` как “runtime-эвристики”.

## Ограничения исследования
- В проекте пока нет нативного подсчёта реальных LLM usage tokens для каждого шага Zapovednik.
- Пороговые значения v1 — эмпирические стартовые; требуют калибровки по 1–2 неделям реальных сессий.

## Синтез
- Да, по жизненному циклу текущая логика фактически “закрытие ведёт к следующему открытию”.
- Для управляемого качества нужно закрывать сессию не по интуиции, а по метрикам: размер, токены, повторы, деградация.
- Оптимальный следующий этап: добавить `zapovednik health` и machine-checkable `recommend_close`.
