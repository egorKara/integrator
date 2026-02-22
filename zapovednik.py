from __future__ import annotations

import json
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
    out = paths.memory_dir / _zap_name(ts)
    if not out.exists():
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
    if cur is None:
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
    return cur


def show(path: Path) -> str:
    return _read_text(path) or ""


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
