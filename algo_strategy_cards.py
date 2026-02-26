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

_TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "tslab": re.compile(r"\btslab\b|тслаб|агент|скрипт|контейнер", re.IGNORECASE),
    "optimization": re.compile(r"оптимиз|границ|минимум|максимум|\bmin\b|\bmax\b|шаг|step", re.IGNORECASE),
    "risk": re.compile(r"риск|плеч|маржин|просадк|drawdown|stop|стоп|sl|take|тейк|tp", re.IGNORECASE),
    "timeframe": re.compile(r"таймфрейм|timeframe|минут|час|дн", re.IGNORECASE),
    "grid": re.compile(r"grid|сетка|сеточ", re.IGNORECASE),
    "indicators": re.compile(r"rsi|macd|ema|sma|ma|parabolic|параболик|скользящ", re.IGNORECASE),
    "providers": re.compile(r"quik|квик|финам|transaq|транзак|binance|bybit|okx|поставщик", re.IGNORECASE),
    "orders": re.compile(r"ордер|заявк|лимит|market|рыночн|стакан", re.IGNORECASE),
}


def _utc_now() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds")


def _fmt_hms(seconds: float) -> str:
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _segment_topics(text: str) -> list[str]:
    out: list[str] = []
    for name, pat in _TOPIC_PATTERNS.items():
        if pat.search(text):
            out.append(name)
    return out


def _pick_highlights(segments: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        topics = _segment_topics(text)
        if not topics:
            continue
        highlights.append(
            {
                "t_start": float(seg.get("start", 0.0)),
                "t_end": float(seg.get("end", 0.0)),
                "hms": _fmt_hms(float(seg.get("start", 0.0))),
                "topics": topics,
                "text": text,
            }
        )
        if len(highlights) >= limit:
            break
    return highlights


def _extract_params_from_segment_text(session_id: str, t_sec: float, text: str) -> list[dict[str, Any]]:
    import algo_params_extract as ape

    hits = ape._hits_from_text(session_id=session_id, source="full_transcript", t_sec=t_sec, text=text)  # type: ignore[attr-defined]
    return [
        {
            "kind": h.kind,
            "value": h.value,
            "t_sec": h.t_sec,
            "context": h.context,
        }
        for h in hits
        if h.kind != "keywords"
    ]


def _extract_params(segments: list[dict[str, Any]], session_id: str, limit: int = 120) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        t0 = float(seg.get("start", 0.0))
        out.extend(_extract_params_from_segment_text(session_id, t0, text))
        if len(out) >= limit:
            break
    return out[:limit]


def _tslab_block_map(topics: list[str]) -> list[str]:
    blocks: list[str] = []
    if "timeframe" in topics:
        blocks.append("Timeframe / BarSeries (источник баров)")
    if "indicators" in topics:
        blocks.append("Indicators (MA/EMA/SMA/RSI/MACD/Parabolic)")
    if "orders" in topics or "risk" in topics:
        blocks.append("Order / Position blocks (Entry/Exit, StopLoss/TakeProfit)")
    if "optimization" in topics:
        blocks.append("Optimizer (min/max/step параметры)")
    if "grid" in topics:
        blocks.append("Grid / Ladder orders (логика сетки ордеров)")
    if "providers" in topics:
        blocks.append("Data provider / Connector settings (QUIK/Finam/etc.)")
    if "tslab" in topics:
        blocks.append("Agent/Script lifecycle (контейнер, замена контракта, запуск/стоп)")
    return blocks


@dataclass(frozen=True)
class StrategyCard:
    session_id: str
    created_utc: str
    transcript_json: str
    transcript_txt: str
    duration_sec: float | None
    segment_count: int
    topics: list[str]
    highlights: list[dict[str, Any]]
    params: list[dict[str, Any]]
    tslab_blocks: list[str]


def build_card(transcript_json_path: Path) -> StrategyCard:
    payload: dict[str, Any] = json.loads(transcript_json_path.read_text(encoding="utf-8"))
    session_id = str(payload.get("session_id") or transcript_json_path.name.split(".transcript.json")[0])
    segments = payload.get("segments", []) or []
    topics_set: set[str] = set()
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        for t in _segment_topics(text):
            topics_set.add(t)
    topics = sorted(topics_set)
    highlights = _pick_highlights(segments)
    params = _extract_params(segments, session_id)
    tslab_blocks = _tslab_block_map(topics)

    txt_path = transcript_json_path.with_suffix("").with_suffix(".txt")
    if not txt_path.exists():
        txt_path = Path(str(transcript_json_path).replace(".transcript.json", ".transcript.txt"))

    return StrategyCard(
        session_id=session_id,
        created_utc=_utc_now(),
        transcript_json=str(transcript_json_path),
        transcript_txt=str(txt_path),
        duration_sec=payload.get("duration_sec"),
        segment_count=len(segments),
        topics=topics,
        highlights=highlights,
        params=params,
        tslab_blocks=tslab_blocks,
    )


def write_card_md(out_md: Path, card: StrategyCard) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("---")
    lines.append("project: AlgoTrading")
    lines.append("type: strategy-card")
    lines.append("status: draft")
    lines.append(f"created: {dt.date.today().isoformat()}")
    lines.append(f"session_id: \"{card.session_id}\"")
    lines.append("tags: [video, strategy, tslab]")
    lines.append("---")
    lines.append("")
    lines.append(f"# Карточка стратегии — {card.session_id}")
    lines.append("")
    lines.append(f"- Transcript JSON: {card.transcript_json}")
    lines.append(f"- Transcript TXT: {card.transcript_txt}")
    if card.duration_sec is not None:
        lines.append(f"- Duration: {card.duration_sec:.1f}s")
    lines.append(f"- Segments: {card.segment_count}")
    if card.topics:
        lines.append(f"- Topics: {', '.join(card.topics)}")
    lines.append("")
    lines.append("## Привязка к TSLab (блоки/узлы)")
    if card.tslab_blocks:
        for b in card.tslab_blocks:
            lines.append(f"- {b}")
    else:
        lines.append("- (не определено)")
    lines.append("")
    lines.append("## Кандидаты параметров (первые 50)")
    if card.params:
        for p in card.params[:50]:
            t = p.get("t_sec")
            hms = "?" if t is None else _fmt_hms(float(t))
            lines.append(f"- {p.get('kind')}={p.get('value')} @ {hms}: {p.get('context')}")
    else:
        lines.append("- (нет)")
    lines.append("")
    lines.append("## Цитаты/сигналы (highlights)")
    for h in card.highlights:
        lines.append(f"- [{h.get('hms')}] ({', '.join(h.get('topics', []))}) {h.get('text')}")
    lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--transcripts-dir", default=str(VAULT_ALGO_ROOT / "Reports" / "TranscriptsFull"))
    p.add_argument("--out-json", default=str(VAULT_ALGO_ROOT / "Reports" / f"strategy_cards_{dt.date.today().isoformat()}.json"))
    p.add_argument("--out-notes-dir", default=str(VAULT_ALGO_ROOT / "Notes" / "StrategyCards"))
    args = p.parse_args()

    tdir = Path(args.transcripts_dir)
    out_json = Path(args.out_json)
    notes_dir = Path(args.out_notes_dir)

    cards: list[StrategyCard] = []
    for pth in sorted(tdir.glob("*.transcript.json")):
        card = build_card(pth)
        cards.append(card)
        write_card_md(notes_dir / f"{card.session_id}.md", card)

    out_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_utc": _utc_now(),
        "transcripts_dir": str(tdir),
        "count": len(cards),
        "cards": [asdict(c) for c in cards],
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

