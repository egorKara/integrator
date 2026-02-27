from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


_RE_HINT = re.compile(
    r"(tslab|grid|сетка|шаг|таймфрейм|rsi|ma|sma|ema|parabolic|стоп|stop|тейк|take|оптимиз|drawdown|просадк|уровн)",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds")


def _extract_hints(text: str) -> list[str]:
    out: list[str] = []
    for m in _RE_HINT.finditer(text):
        s = m.group(0).lower()
        if s not in out:
            out.append(s)
    return out[:20]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--samples-json", required=True)
    p.add_argument("--out-md", required=True)
    args = p.parse_args()

    src = Path(args.samples_json)
    payload: dict[str, Any] = json.loads(src.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    stamp = dt.date.today().isoformat()

    lines: list[str] = []
    lines.append("---")
    lines.append("project: AlgoTrading")
    lines.append("type: report")
    lines.append("status: draft")
    lines.append(f"created: {stamp}")
    lines.append("tags: [video, samples, transcript, algotrading]")
    lines.append("---")
    lines.append("")
    lines.append("# C:\\Video — выборочная транскрипция (семплы)")
    lines.append("")
    lines.append(f"- Source: {src}")
    lines.append(f"- Created (UTC): {_utc_now()}")
    lines.append(f"- Model: {payload.get('model_size')}")
    lines.append(f"- Segment sec: {payload.get('segment_sec')}")
    lines.append(f"- Positions: {payload.get('positions')}")
    lines.append("")

    for it in items:
        session_id = it.get("session_id", "")
        samples = it.get("samples", [])
        all_text = " ".join([s.get("text", "") for s in samples if isinstance(s, dict)])
        hints = _extract_hints(all_text)

        lines.append(f"## {session_id}")
        if hints:
            lines.append(f"- Hints: {', '.join(hints)}")
        for s in samples:
            if not isinstance(s, dict):
                continue
            start = s.get("start_sec")
            dur = s.get("duration_sec")
            text = (s.get("text") or "").strip()
            if text:
                lines.append(f"- [{start}s +{dur}s] {text}")
        lines.append("")

    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

