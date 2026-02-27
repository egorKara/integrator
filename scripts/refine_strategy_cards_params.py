from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VAULT_ALGO_ROOT = REPO_ROOT / "vault" / "Projects" / "AlgoTrading"
DEFAULT_NOTES_DIR = VAULT_ALGO_ROOT / "Notes" / "StrategyCards"
DEFAULT_TRANSCRIPTS_DIR = VAULT_ALGO_ROOT / "Reports" / "TranscriptsFull"
DEFAULT_REPORT_DIR = VAULT_ALGO_ROOT / "Reports"

PARAM_SECTION_HEADERS = (
    "## Параметры для проверки (до 50 вариантов)",
    "## Кандидаты параметров (первые 50)",
)

PARAM_LINE_RE = re.compile(
    r"^- (?P<kind>[a-zA-Z_]+)=(?P<value>.+?)\s+@\s+(?P<time_part>\[\[.+?\]\]|\d{2}:\d{2}:\d{2})\s*:\s*(?P<context>.*)$"
)
LINK_HMS_RE = re.compile(r"#t=(\d{2}:\d{2}:\d{2})\|")
NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")

STOP_RE = re.compile(r"стоп|stop|sl|stoploss", re.IGNORECASE)
TAKE_RE = re.compile(r"тейк|take|tp|takeprofit", re.IGNORECASE)
TRAIL_RE = re.compile(r"трейл|trailing", re.IGNORECASE)
PARTIAL_RE = re.compile(r"частич|половин|измен.*позиц|закрыт.*част", re.IGNORECASE)
FORMULA_RE = re.compile(r"формул|умнож|делен|скоб|процент от|от цены|цена вход", re.IGNORECASE)
OPT_RE = re.compile(r"оптим|диапазон|границ|подбор|шаг|min|max", re.IGNORECASE)
ATR_RE = re.compile(r"atr|а[тt]р|adr", re.IGNORECASE)
CANDLE_RE = re.compile(r"свеч", re.IGNORECASE)
TIMEWINDOW_RE = re.compile(r"время|календар|0-0|часов|минут", re.IGNORECASE)


def _hms_to_sec(hms: str) -> int:
    hh, mm, ss = [int(x) for x in hms.split(":")]
    return hh * 3600 + mm * 60 + ss


def _ru_plural(n: float, one: str, few: str, many: str) -> str:
    x = abs(int(round(n)))
    d10 = x % 10
    d100 = x % 100
    if d10 == 1 and d100 != 11:
        return one
    if 2 <= d10 <= 4 and not (12 <= d100 <= 14):
        return few
    return many


def _normalize_num(num_text: str) -> str:
    s = num_text.replace(",", ".").strip()
    try:
        val = float(s)
    except ValueError:
        return num_text.strip()
    if abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:.4f}".rstrip("0").rstrip(".")


def _normalize_value(kind: str, value: str) -> str:
    raw = value.strip()
    low = raw.lower().replace(",", ".")
    m = NUM_RE.search(low)
    if not m:
        return raw
    num_str = _normalize_num(m.group(0))
    try:
        num_float = float(num_str)
    except ValueError:
        num_float = 0.0

    if kind == "percent":
        return f"{num_str}%"
    if kind == "contracts":
        return f"{num_str} {_ru_plural(num_float, 'контракт', 'контракта', 'контрактов')}"
    if kind == "points":
        return f"{num_str} {_ru_plural(num_float, 'пункт', 'пункта', 'пунктов')}"
    if kind == "timeframe":
        if re.search(r"час|\bh\b|h$", low):
            return f"{num_str} {_ru_plural(num_float, 'час', 'часа', 'часов')}"
        if re.search(r"дн|day", low):
            return f"{num_str} {_ru_plural(num_float, 'день', 'дня', 'дней')}"
        return f"{num_str} {_ru_plural(num_float, 'минута', 'минуты', 'минут')}"
    return raw


def _find_nearest_segment_index(segments: list[dict[str, Any]], t_sec: int) -> int:
    best_idx = 0
    best_dist = float("inf")
    for idx, seg in enumerate(segments):
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        if start <= t_sec <= end:
            return idx
        dist = min(abs(t_sec - start), abs(t_sec - end))
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx


def _window_text(segments: list[dict[str, Any]], idx: int, radius: int = 1) -> str:
    start = max(0, idx - radius)
    end = min(len(segments), idx + radius + 1)
    chunks: list[str] = []
    for seg in segments[start:end]:
        text = str(seg.get("text", "")).strip()
        if text:
            chunks.append(text)
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def _build_summary(kind: str, context_window: str) -> str:
    text = context_window.lower()
    is_stop = bool(STOP_RE.search(text))
    is_take = bool(TAKE_RE.search(text))
    is_trail = bool(TRAIL_RE.search(text))
    is_partial = bool(PARTIAL_RE.search(text))
    is_formula = bool(FORMULA_RE.search(text))
    is_opt = bool(OPT_RE.search(text))
    is_atr = bool(ATR_RE.search(text))
    is_candle = bool(CANDLE_RE.search(text))
    is_time_window = bool(TIMEWINDOW_RE.search(text))

    parts: list[str] = []
    if kind == "contracts":
        if is_partial:
            parts.append("Показан сценарий частичного управления объемом позиции.")
        else:
            parts.append("Параметр используется для задания объема позиции.")
    elif kind == "points":
        if is_stop and is_take:
            parts.append("Значение используется как расстояние в пунктах для стопа и тейка.")
        elif is_stop:
            parts.append("Значение используется как расстояние в пунктах для стоп-лосса.")
        elif is_take:
            parts.append("Значение используется как расстояние в пунктах для тейк-профита.")
        else:
            parts.append("Значение используется как абсолютная дистанция в пунктах.")
        if is_opt:
            parts.append("Упоминается как кандидат диапазона оптимизации.")
    elif kind == "percent":
        if is_candle:
            parts.append("Процент берется как доля диапазона свечи.")
        elif is_formula:
            parts.append("Показан расчет процента от базовой цены через формулу.")
        else:
            parts.append("Значение используется как процентный коэффициент в расчетах стратегии.")
        if is_stop and is_take:
            parts.append("Применяется для stop-loss и take-profit.")
        elif is_stop:
            parts.append("Применяется для stop-loss.")
        elif is_take:
            parts.append("Применяется для take-profit.")
        elif is_trail:
            parts.append("Применяется в логике трейлинга.")
    elif kind == "timeframe":
        if is_time_window and not (is_stop or is_take):
            parts.append("Рассматривается настройка временного окна и границ времени в стратегии.")
        else:
            parts.append("Рассматривается влияние таймфрейма на поведение стратегии.")
        if is_stop or is_take:
            parts.append("На этом ТФ отдельно подбираются параметры stop/take.")
        if is_opt:
            parts.append("Параметр обсуждается в контексте оптимизации.")
    elif kind == "step":
        parts.append("Параметр шага используется для перебора значений в оптимизации.")
    else:
        parts.append("Параметр обсуждается в практической настройке скрипта.")

    if is_atr and kind in {"points", "percent"}:
        parts.append("В расчете учитывается привязка к волатильности (ATR/ADR).")
    return " ".join(parts)


def _extract_hms(time_part: str) -> str | None:
    if time_part.startswith("[["):
        m = LINK_HMS_RE.search(time_part)
        if m:
            return m.group(1)
        return None
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", time_part):
        return time_part
    return None


def _load_transcript_segments(transcript_path: Path) -> list[dict[str, Any]]:
    payload: dict[str, Any] = json.loads(transcript_path.read_text(encoding="utf-8"))
    segments = payload.get("segments", [])
    if not isinstance(segments, list):
        return []
    return [s for s in segments if isinstance(s, dict)]


def _find_param_section_bounds(lines: list[str]) -> tuple[int, int] | None:
    start = -1
    for i, line in enumerate(lines):
        if line.strip() in PARAM_SECTION_HEADERS:
            start = i
            break
    if start < 0:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def refine_card(
    card_path: Path,
    transcripts_dir: Path,
    transcript_cache: dict[Path, list[dict[str, Any]]],
) -> tuple[bool, int, int]:
    original = card_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    bounds = _find_param_section_bounds(lines)
    if bounds is None:
        return False, 0, 0
    start, end = bounds

    session_id = card_path.stem
    transcript_path = transcripts_dir / f"{session_id}.transcript.json"
    if transcript_path not in transcript_cache:
        if transcript_path.exists():
            transcript_cache[transcript_path] = _load_transcript_segments(transcript_path)
        else:
            transcript_cache[transcript_path] = []
    segments = transcript_cache[transcript_path]

    total = 0
    changed = 0
    for i in range(start + 1, end):
        line = lines[i]
        m = PARAM_LINE_RE.match(line)
        if not m:
            continue
        total += 1
        kind = m.group("kind")
        value = m.group("value")
        time_part = m.group("time_part")
        old_context = m.group("context").strip()

        normalized_value = _normalize_value(kind, value)
        hms = _extract_hms(time_part)
        if hms and segments:
            t_sec = _hms_to_sec(hms)
            idx = _find_nearest_segment_index(segments, t_sec)
            ctx = _window_text(segments, idx, radius=1)
            summary = _build_summary(kind, ctx)
        else:
            summary = _build_summary(kind, old_context)

        new_line = f"- {kind}={normalized_value} @ {time_part}: {summary}"
        if new_line != line:
            lines[i] = new_line
            changed += 1

    if changed:
        card_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True, total, changed
    return False, total, changed


def write_report(report_dir: Path, stats: dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = report_dir / f"strategy_cards_param_refine_report_{stamp}.md"

    lines: list[str] = []
    lines.append("---")
    lines.append("project: AlgoTrading")
    lines.append("type: report")
    lines.append("status: done")
    lines.append(f"created: {dt.date.today().isoformat()}")
    lines.append("tags: [strategy-cards, params, cleanup, asl]")
    lines.append("---")
    lines.append("")
    lines.append("# Очистка фраз в разделе параметров (StrategyCards)")
    lines.append("")
    lines.append("## Тезис")
    lines.append("- Сырые ASR-фрагменты дают некорректные и незавершенные формулировки в карточках.")
    lines.append("")
    lines.append("## Антитезис")
    lines.append("- Полное переписывание вручную рискованно: теряется связь с таймкодами и воспроизводимость.")
    lines.append("")
    lines.append("## Синтез")
    lines.append("- Для каждой строки параметра сохраняется исходный таймкод/ссылка.")
    lines.append("- Текст фразы восстанавливается по окну соседних сегментов из `transcript.json`.")
    lines.append("- Значения параметров нормализуются в человекочитаемый вид (контракты/пункты/%/ТФ).")
    lines.append("- Итог: завершенные фразы без мусорных ASR-обрывков.")
    lines.append("")
    lines.append("## Итог по запуску")
    lines.append(f"- Файлов проверено: {stats['files_total']}")
    lines.append(f"- Файлов изменено: {stats['files_changed']}")
    lines.append(f"- Строк параметров обработано: {stats['param_lines_total']}")
    lines.append(f"- Строк параметров переписано: {stats['param_lines_changed']}")
    lines.append("")
    lines.append("## Измененные файлы")
    for rel in stats["changed_files"]:
        lines.append(f"- {rel}")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--notes-dir", default=str(DEFAULT_NOTES_DIR))
    p.add_argument("--transcripts-dir", default=str(DEFAULT_TRANSCRIPTS_DIR))
    p.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    args = p.parse_args()

    notes_dir = Path(args.notes_dir)
    transcripts_dir = Path(args.transcripts_dir)
    report_dir = Path(args.report_dir)

    transcript_cache: dict[Path, list[dict[str, Any]]] = {}
    files_total = 0
    files_changed = 0
    param_lines_total = 0
    param_lines_changed = 0
    changed_files: list[str] = []

    for card in sorted(notes_dir.glob("*.md")):
        files_total += 1
        changed, total, changed_count = refine_card(card, transcripts_dir, transcript_cache)
        param_lines_total += total
        param_lines_changed += changed_count
        if changed:
            files_changed += 1
            changed_files.append(str(card.relative_to(REPO_ROOT)))

    stats = {
        "files_total": files_total,
        "files_changed": files_changed,
        "param_lines_total": param_lines_total,
        "param_lines_changed": param_lines_changed,
        "changed_files": changed_files,
    }
    report_path = write_report(report_dir, stats)
    print(json.dumps({"status": "ok", "stats": stats, "report": str(report_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
