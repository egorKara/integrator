from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class IdeaRow:
    title: str
    priority: str
    benefit: str
    risk: str
    time: str
    tags: str
    path: str
    snippet: str
    score: int


PRIORITY_SCORE = {"high": 3, "medium": 2, "low": 1}
BENEFIT_SCORE = {"high": 3, "medium": 2, "low": 1}
RISK_SCORE = {"high": -2, "medium": -1, "low": 0}
TIME_SCORE = {"high": -2, "medium": -1, "low": 0}

RISK_KEYWORDS = {
    "security": "high",
    "proxy": "high",
    "vps": "high",
    "leak": "high",
    "auth": "high",
    "critical": "high",
    "migration": "medium",
    "refactor": "medium",
}

TIME_KEYWORDS = {
    "refactor": "high",
    "migration": "high",
    "pipeline": "high",
    "index": "medium",
    "watcher": "medium",
    "automation": "medium",
    "script": "low",
}


def _detect_weight(text: str, mapping: dict[str, str], default: str) -> str:
    lower = text.lower()
    for key, value in mapping.items():
        if key in lower:
            return value
    return default


def _compute_score(priority: str, benefit: str, risk: str, time: str) -> int:
    return (
        PRIORITY_SCORE.get(priority, 1)
        + BENEFIT_SCORE.get(benefit, 1)
        + RISK_SCORE.get(risk, 0)
        + TIME_SCORE.get(time, 0)
    )


def parse_items(text: str) -> list[IdeaRow]:
    items: list[IdeaRow] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("- [ ]"):
            i += 1
            continue
        title_part, meta_part = (line[5:].split("|", 1) + [""])[:2]
        title = title_part.strip()
        meta = meta_part.strip()
        priority = _extract_field(meta, "priority", "low")
        benefit = _extract_field(meta, "benefit", "medium")
        tags = _extract_field(meta, "tags", "-")
        path = ""
        snippet = ""
        if i + 1 < len(lines) and "path:" in lines[i + 1]:
            path = lines[i + 1].split("path:", 1)[1].strip()
        if i + 2 < len(lines) and "snippet:" in lines[i + 2]:
            snippet = lines[i + 2].split("snippet:", 1)[1].strip()
        combined = " ".join([title, snippet])
        risk = _detect_weight(combined, RISK_KEYWORDS, "low")
        time = _detect_weight(combined, TIME_KEYWORDS, "medium")
        score = _compute_score(priority, benefit, risk, time)
        items.append(
            IdeaRow(
                title=title,
                priority=priority,
                benefit=benefit,
                risk=risk,
                time=time,
                tags=tags,
                path=path,
                snippet=snippet,
                score=score,
            )
        )
        i += 3
    return items


def _extract_field(meta: str, name: str, default: str) -> str:
    match = re.search(rf"{name}=([^|]+)", meta)
    if not match:
        return default
    return match.group(1).strip()


def write_output(items: list[IdeaRow], output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Ideas Checklist (Prioritized)")
    lines.append("")
    lines.append(f"Items: {len(items)}")
    lines.append("")
    for item in items:
        lines.append(
            "- [ ] "
            + f"{item.title} | score={item.score} | "
            + f"benefit={item.benefit} | risk={item.risk} | time={item.time} | "
            + f"priority={item.priority} | tags={item.tags}"
        )
        lines.append(f"  - path: {item.path}")
        lines.append(f"  - snippet: {item.snippet}")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    source = Path(args.input)
    if not source.exists():
        return 2
    text = source.read_text(encoding="utf-8")
    items = parse_items(text)
    items.sort(key=lambda item: item.score, reverse=True)
    write_output(items, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
