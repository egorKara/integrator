from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
VAULT_ALGO_ROOT = REPO_ROOT / "vault" / "Projects" / "AlgoTrading"


@dataclass(frozen=True)
class ParamHit:
    session_id: str
    source: str
    t_sec: float | None
    kind: str
    value: str
    context: str


_RE_NUMBER = r"(?P<num>\d+(?:[.,]\d+)?)"
_RE_PERCENT = re.compile(rf"{_RE_NUMBER}\s*%", re.IGNORECASE)
_RE_TIMEFRAME = re.compile(
    rf"{_RE_NUMBER}\s*(?:мин(?:ут[а-я]*)?|m|minute|час(?:[а-я]*)?|h|hour|дн(?:[а-я]*)?|day)",
    re.IGNORECASE,
)
_RE_CONTRACT = re.compile(rf"{_RE_NUMBER}\s*(?:контракт(?:[а-я]*)?|лот(?:[а-я]*)?)", re.IGNORECASE)
_RE_POINTS = re.compile(rf"{_RE_NUMBER}\s*(?:пункт(?:[а-я]*)?|pt|points)", re.IGNORECASE)
_RE_STEP = re.compile(rf"(?:шаг|step)\s*[:=]?\s*{_RE_NUMBER}", re.IGNORECASE)
_RE_KEYWORDS = re.compile(
    r"(таймфрейм|timeframe|stop|стоп|take|тейк|tp|sl|rsi|macd|ema|sma|ma|parabolic|параболик|grid|сетка|оптимиз|границ)",
    re.IGNORECASE,
)


def _normalize_num(s: str) -> str:
    return s.replace(",", ".")


def _hits_from_text(
    *,
    session_id: str,
    source: str,
    t_sec: float | None,
    text: str,
    max_context: int = 220,
) -> list[ParamHit]:
    out: list[ParamHit] = []
    if not text.strip():
        return out

    def add(kind: str, value: str, context: str) -> None:
        ctx = context.strip().replace("\n", " ")
        if len(ctx) > max_context:
            ctx = ctx[: max_context - 1].rstrip() + "…"
        out.append(
            ParamHit(
                session_id=session_id,
                source=source,
                t_sec=t_sec,
                kind=kind,
                value=value,
                context=ctx,
            )
        )

    for m in _RE_TIMEFRAME.finditer(text):
        add("timeframe", _normalize_num(m.group(0)), text)
    for m in _RE_PERCENT.finditer(text):
        add("percent", _normalize_num(m.group(0)), text)
    for m in _RE_CONTRACT.finditer(text):
        add("contracts", _normalize_num(m.group(0)), text)
    for m in _RE_POINTS.finditer(text):
        add("points", _normalize_num(m.group(0)), text)
    for m in _RE_STEP.finditer(text):
        add("step", _normalize_num(m.group(0)), text)
    if _RE_KEYWORDS.search(text):
        kws = sorted({k.lower() for k in _RE_KEYWORDS.findall(text)})
        add("keywords", ", ".join(kws), text)
    return out


def extract_from_samples(samples_json: Path) -> list[ParamHit]:
    payload: dict[str, Any] = json.loads(samples_json.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    hits: list[ParamHit] = []
    for it in items:
        session_id = str(it.get("session_id", ""))
        for s in it.get("samples", []):
            if not isinstance(s, dict):
                continue
            base = float(s.get("start_sec", 0.0))
            for seg in s.get("segments", []):
                if not isinstance(seg, dict):
                    continue
                start = float(seg.get("start", 0.0))
                text = str(seg.get("text", "")).strip()
                if not text:
                    continue
                t_abs = round(base + start, 3)
                hits.extend(
                    _hits_from_text(
                        session_id=session_id,
                        source=f"samples:{samples_json.name}",
                        t_sec=t_abs,
                        text=text,
                    )
                )
    return hits


def extract_from_specs(specs_dir: Path) -> list[ParamHit]:
    hits: list[ParamHit] = []
    re_ts_line = re.compile(r"^\*\*\((\d\d:\d\d:\d\d)\)\*\*\s*(.*)$")

    for p in sorted(specs_dir.glob("*.md")):
        session_id = p.stem
        text = p.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            m = re_ts_line.match(line.strip())
            if not m:
                continue
            ts = m.group(1)
            rest = m.group(2)
            h, mm, ss = [int(x) for x in ts.split(":")]
            t_sec = float(h * 3600 + mm * 60 + ss)
            hits.extend(
                _hits_from_text(
                    session_id=session_id,
                    source=f"spec:{p.name}",
                    t_sec=t_sec,
                    text=rest,
                )
            )
    return hits


def write_outputs(out_json: Path, out_md: Path, hits: list[ParamHit]) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "created_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds"),
        "hits": [asdict(h) for h in hits],
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    by_kind: dict[str, int] = {}
    by_session: dict[str, int] = {}
    for h in hits:
        by_kind[h.kind] = by_kind.get(h.kind, 0) + 1
        by_session[h.session_id] = by_session.get(h.session_id, 0) + 1

    top_sessions = sorted(by_session.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
    top_kinds = sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0]))

    lines: list[str] = []
    lines.append("---")
    lines.append("project: AlgoTrading")
    lines.append("type: report")
    lines.append("status: draft")
    lines.append(f"created: {dt.date.today().isoformat()}")
    lines.append("tags: [params, extraction, algotrading]")
    lines.append("---")
    lines.append("")
    lines.append("# Кандидаты параметров/конфигов (из транскриптов)")
    lines.append("")
    lines.append(f"- Hits: {len(hits)}")
    lines.append(f"- JSON: {out_json}")
    lines.append("")
    lines.append("## По типам")
    for k, c in top_kinds:
        lines.append(f"- {k}: {c}")
    lines.append("")
    lines.append("## Топ-сессии по количеству совпадений")
    for sid, c in top_sessions:
        lines.append(f"- {sid}: {c}")
    lines.append("")
    lines.append("## Примеры (первые 60)")
    lines.append("")
    for h in hits[:60]:
        t = "?" if h.t_sec is None else f"{h.t_sec:.1f}s"
        lines.append(f"- [{h.session_id}] {h.kind}={h.value} @ {t} ({h.source}): {h.context}")
    lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--samples-json", required=True)
    p.add_argument("--specs-dir", default=str(VAULT_ALGO_ROOT / "Specs"))
    p.add_argument("--out-dir", default=str(VAULT_ALGO_ROOT / "Reports"))
    p.add_argument("--out-prefix", default="params_candidates")
    args = p.parse_args()

    samples_json = Path(args.samples_json)
    specs_dir = Path(args.specs_dir)
    out_dir = Path(args.out_dir)
    stamp = dt.date.today().isoformat()

    hits = []
    hits.extend(extract_from_samples(samples_json))
    if specs_dir.exists():
        hits.extend(extract_from_specs(specs_dir))

    out_json = out_dir / f"{args.out_prefix}_{stamp}.json"
    out_md = out_dir / f"{args.out_prefix}_{stamp}.md"
    write_outputs(out_json, out_md, hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

