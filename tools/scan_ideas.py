from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from utils import _write_text_atomic

@dataclass(frozen=True, slots=True)
class IdeaItem:
    title: str
    path: Path
    snippet: str
    priority: str
    benefit: str
    tags: tuple[str, ...]


IDEA_PATTERNS = (
    r"\bidea\b",
    r"\bproposal\b",
    r"\bbacklog\b",
    r"\btodo\b",
    r"\bидея\b",
    r"\bпредложение\b",
)

KEYWORD_BENEFIT = (
    ("automation", "high"),
    ("integrator", "high"),
    ("localai", "high"),
    ("rag", "high"),
    ("security", "high"),
)

KEYWORD_PRIORITY = (
    ("p0", "high"),
    ("urgent", "high"),
    ("critical", "high"),
    ("p1", "medium"),
)


def _detect_priority(text: str) -> str:
    lower = text.lower()
    for key, value in KEYWORD_PRIORITY:
        if key in lower:
            return value
    return "low"


def _detect_benefit(text: str) -> str:
    lower = text.lower()
    for key, value in KEYWORD_BENEFIT:
        if key in lower:
            return value
    return "medium"


def _extract_title(lines: list[str], fallback: str) -> str:
    for line in lines[:30]:
        if line.strip().startswith("#"):
            return line.strip().lstrip("#").strip()
    return fallback


def scan_file(path: Path, patterns: list[re.Pattern[str]]) -> list[IdeaItem]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    lines = text.splitlines()
    title = _extract_title(lines, path.stem)
    items: list[IdeaItem] = []
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        if not any(pattern.search(line) for pattern in patterns):
            continue
        context = " ".join([line.strip()])
        priority = _detect_priority(context)
        benefit = _detect_benefit(context)
        tags = tuple(sorted({tag for tag, _ in KEYWORD_BENEFIT if tag in context.lower()}))
        snippet = context[:240]
        items.append(
            IdeaItem(
                title=title,
                path=path,
                snippet=snippet,
                priority=priority,
                benefit=benefit,
                tags=tags,
            )
        )
    return items


def write_markdown(items: list[IdeaItem], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Ideas Checklist")
    lines.append("")
    lines.append(f"Items: {len(items)}")
    lines.append("")
    for item in items:
        rel = str(item.path)
        tags = ", ".join(item.tags) if item.tags else "-"
        lines.append(f"- [ ] {item.title} | priority={item.priority} | benefit={item.benefit} | tags={tags}")
        lines.append(f"  - path: {rel}")
        lines.append(f"  - snippet: {item.snippet}")
    _write_text_atomic(output_path, "\n".join(lines) + "\n", backup=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--ignore", nargs="*", default=[])
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        return 2
    ignore = set(args.ignore)
    patterns = [re.compile(pat, re.IGNORECASE) for pat in IDEA_PATTERNS]
    items: list[IdeaItem] = []
    for path in root.rglob("*.md"):
        if any(part in ignore for part in path.parts):
            continue
        items.extend(scan_file(path, patterns))
    items.sort(key=lambda item: (item.priority, item.benefit, item.title))
    write_markdown(items, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
