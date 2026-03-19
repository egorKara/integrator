from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from utils import _read_text, _write_text_atomic


@dataclass(frozen=True)
class ZapPaths:
    memory_dir: Path
    current_file: Path


def _timestamp_compact() -> str:
    return time.strftime("%Y-%m-%d-%H%M", time.localtime())


def _timestamp_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _find_memory_dir(start: Path) -> Path:
    cur = start.resolve()
    for base in [cur, *cur.parents]:
        cand = base / ".trae" / "memory"
        if cand.is_dir():
            return cand
    cand = Path(__file__).resolve().parent / ".trae" / "memory"
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def _paths(start: Path | None = None) -> ZapPaths:
    base = Path.cwd() if start is None else start
    memory_dir = _find_memory_dir(base)
    current_file = memory_dir / "zapovednik_current.txt"
    return ZapPaths(memory_dir=memory_dir, current_file=current_file)


def _zap_name(ts_compact: str) -> str:
    return f"Заповедник промтов - {ts_compact}.md"


def _zap_name_with_index(ts_compact: str, index: int) -> str:
    if index <= 0:
        return _zap_name(ts_compact)
    return f"Заповедник промтов - {ts_compact}-{index:02d}.md"


def _next_session_path(memory_dir: Path, ts_compact: str) -> Path:
    idx = 0
    while True:
        candidate = memory_dir / _zap_name_with_index(ts_compact, idx)
        if not candidate.exists():
            return candidate
        idx += 1


def _get_current_path(paths: ZapPaths) -> Path | None:
    text = _read_text(paths.current_file)
    if not text:
        return None
    raw = text.strip()
    if not raw:
        return None
    try:
        p = Path(raw)
    except OSError:
        return None
    return p if p.exists() else None


def start_session(*, start: Path | None = None) -> Path:
    paths = _paths(start)
    ts = _timestamp_compact()
    out = _next_session_path(paths.memory_dir, ts)
    header = f"## Сессия: {ts}\n\n"
    _write_text_atomic(out, header, backup=True)
    _write_text_atomic(paths.current_file, str(out) + "\n", backup=True)
    return out


def current_session_path(*, start: Path | None = None) -> Path:
    paths = _paths(start)
    cur = _get_current_path(paths)
    return cur or start_session(start=start)


def append_message(
    role: str,
    text: str,
    *,
    meta: dict[str, object] | None = None,
    path: Path | None = None,
    start: Path | None = None,
) -> Path:
    paths = _paths(start)
    cur = path.resolve() if path is not None else _get_current_path(paths)
    if cur is None or (path is None and _is_session_closed(cur)):
        cur = start_session(start=start)
    if path is not None:
        _write_text_atomic(paths.current_file, str(cur) + "\n", backup=True)
    meta_obj: dict[str, object] = dict(meta or {})
    meta_obj.setdefault("ts", _timestamp_iso())
    meta_obj.setdefault("role", role)
    meta_obj.setdefault("cwd", str(Path.cwd()))

    payload = json.dumps(meta_obj, ensure_ascii=False, sort_keys=True)
    entry = f"### msg\n- meta: {payload}\n- text:\n\n{text.rstrip()}\n\n"
    existing = _read_text(cur) or ""
    _write_text_atomic(cur, existing + entry, backup=True)
    return cur


def finalize_session(
    *,
    path: Path | None = None,
    start: Path | None = None,
) -> Path:
    paths = _paths(start)
    cur = path or _get_current_path(paths) or start_session(start=start)
    text = _read_text(cur) or ""
    marker = "\n## Итоги и статистика"
    base = text
    cut = base.find(marker)
    if cut >= 0:
        preserve_from = base.find("\n### msg", cut + 1)
        if preserve_from >= 0:
            base = base[:cut].rstrip() + "\n" + base[preserve_from:].lstrip("\n")
        else:
            base = base[:cut].rstrip() + "\n"
    stats = _compute_stats(base)
    block = _format_stats(stats)
    _write_text_atomic(cur, base.rstrip() + "\n\n" + block, backup=True)
    if path is None:
        _write_text_atomic(paths.current_file, "", backup=True)
    return cur


def show(path: Path) -> str:
    return _read_text(path) or ""


def session_health(
    *,
    path: Path | None = None,
    start: Path | None = None,
    context_window_tokens: int = 200000,
    message_soft_limit: int = 40,
    size_soft_limit_kb: int = 180,
    token_soft_ratio: float = 0.70,
    token_hard_ratio: float = 0.85,
    min_repeated_tokens: int = 5,
    min_repeat_frequency: int = 3,
    score_threshold: float = 0.75,
    latency_degradation: float = 0.0,
) -> dict[str, object]:
    cur = path.resolve() if path is not None else current_session_path(start=start)
    text = _read_text(cur) or ""
    stats = _compute_stats(text)
    file_size_bytes = len(text.encode("utf-8"))
    file_size_kb = file_size_bytes / 1024.0
    approx_tokens = int(math.ceil(max(0, len(text)) / 4.0))
    context_window = max(1, int(context_window_tokens))
    token_ratio = float(approx_tokens) / float(context_window)
    size_limit_kb = max(1, int(size_soft_limit_kb))
    size_ratio = float(file_size_kb) / float(size_limit_kb)
    repeats_raw = stats.get("repeats", [])
    repeated_tokens_count = 0
    if isinstance(repeats_raw, list):
        repeated_tokens_count = sum(
            1
            for item in repeats_raw
            if isinstance(item, (list, tuple))
            and len(item) == 2
            and isinstance(item[1], int)
            and int(item[1]) >= int(min_repeat_frequency)
        )
    denom = max(1, int(min_repeated_tokens))
    repetition_ratio = min(1.0, float(repeated_tokens_count) / float(denom))
    lat = max(0.0, min(1.0, float(latency_degradation)))
    close_score = size_ratio * 0.35 + token_ratio * 0.4 + repetition_ratio * 0.15 + lat * 0.1
    messages_total = stats.get("messages_total", 0)
    messages_total_int = int(messages_total) if isinstance(messages_total, int) else 0
    question_marks = stats.get("question_marks", 0)
    question_marks_int = int(question_marks) if isinstance(question_marks, int) else 0
    signal_messages = messages_total_int >= int(message_soft_limit)
    signal_size = file_size_kb >= float(size_limit_kb)
    signal_token_soft = token_ratio >= float(token_soft_ratio)
    signal_token_hard = token_ratio >= float(token_hard_ratio)
    signal_repetition = repeated_tokens_count >= int(min_repeated_tokens)
    reasons: list[str] = []
    if signal_messages:
        reasons.append("messages_soft_limit")
    if signal_size:
        reasons.append("size_soft_limit")
    if signal_token_soft:
        reasons.append("token_soft_limit")
    if signal_token_hard:
        reasons.append("token_hard_limit")
    if signal_repetition:
        reasons.append("repetition_signal")
    if close_score >= float(score_threshold):
        reasons.append("score_threshold")
    recommend_close = bool(signal_token_hard or close_score >= float(score_threshold))
    if not recommend_close and (signal_messages and (signal_size or signal_token_soft or signal_repetition)):
        recommend_close = True
    return {
        "path": str(cur),
        "file_size_bytes": int(file_size_bytes),
        "file_size_kb": round(file_size_kb, 3),
        "messages_total": messages_total_int,
        "question_marks": question_marks_int,
        "approx_tokens": int(approx_tokens),
        "context_window_tokens": int(context_window),
        "token_ratio": round(token_ratio, 6),
        "size_soft_limit_kb": int(size_limit_kb),
        "size_ratio": round(size_ratio, 6),
        "repeated_tokens_count": int(repeated_tokens_count),
        "repetition_ratio": round(repetition_ratio, 6),
        "close_score": round(close_score, 6),
        "recommend_close": bool(recommend_close),
        "recommend_close_reasons": reasons,
        "session_closed": bool(_is_session_closed(cur)),
        "thresholds": {
            "message_soft_limit": int(message_soft_limit),
            "token_soft_ratio": float(token_soft_ratio),
            "token_hard_ratio": float(token_hard_ratio),
            "min_repeated_tokens": int(min_repeated_tokens),
            "min_repeat_frequency": int(min_repeat_frequency),
            "score_threshold": float(score_threshold),
        },
        "signals": {
            "messages_soft_limit": bool(signal_messages),
            "size_soft_limit": bool(signal_size),
            "token_soft_limit": bool(signal_token_soft),
            "token_hard_limit": bool(signal_token_hard),
            "repetition_signal": bool(signal_repetition),
        },
    }


_STOP = {
    "и",
    "в",
    "во",
    "на",
    "не",
    "что",
    "это",
    "я",
    "ты",
    "мы",
    "вы",
    "он",
    "она",
    "они",
    "оно",
    "а",
    "но",
    "или",
    "же",
    "ли",
    "как",
    "то",
    "к",
    "по",
    "за",
    "у",
    "из",
    "для",
    "с",
    "со",
    "от",
    "до",
    "при",
    "над",
    "под",
    "про",
    "без",
    "же",
    "все",
    "всё",
}


def _iter_msg_texts(full: str) -> Iterable[str]:
    blocks = full.split("### msg")
    for b in blocks[1:]:
        m = re.search(r"\n- text:\n\n(.*)", b, flags=re.DOTALL)
        if not m:
            continue
        body = m.group(1)
        body = body.split("\n\n###", 1)[0]
        yield body.strip()


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9_]{2,}", text.lower())
    out = [w for w in words if len(w) >= 3 and w not in _STOP]
    return out


def _top_counts(tokens: list[str], limit: int = 12) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return items[: max(0, int(limit))]


def _compute_stats(full: str) -> dict[str, object]:
    msgs = list(_iter_msg_texts(full))
    tokens: list[str] = []
    question_marks = 0
    for m in msgs:
        tokens.extend(_tokenize(m))
        question_marks += m.count("?")
    top = _top_counts(tokens, limit=12)
    repeats = [(w, c) for w, c in top if c >= 2]
    return {
        "messages_total": len(msgs),
        "question_marks": question_marks,
        "top_tokens": top,
        "repeats": repeats,
    }


def _format_stats(stats: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append("## Итоги и статистика\n")
    lines.append(f"- messages_total: {stats.get('messages_total', 0)}")
    lines.append(f"- question_marks: {stats.get('question_marks', 0)}")
    lines.append("- session_closed: true")
    top = stats.get("top_tokens", [])
    if isinstance(top, list) and top:
        lines.append("- top_tokens:")
        for item in top:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                lines.append(f"  - {item[0]}: {item[1]}")
    rep = stats.get("repeats", [])
    if isinstance(rep, list) and rep:
        lines.append("- repeats>=2:")
        for item in rep:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                lines.append(f"  - {item[0]}: {item[1]}")
    return "\n".join(lines).rstrip() + "\n"


def _is_session_closed(path: Path) -> bool:
    text = _read_text(path) or ""
    return "## Итоги и статистика" in text and "- session_closed: true" in text
