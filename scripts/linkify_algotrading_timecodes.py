from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

PROJECT_ROOT = Path(r"C:\integrator\vault\Projects\AlgoTrading")
VIDEO_SOURCE_ROOT = Path(r"C:\Video")
VIDEO_TARGET_DIR = PROJECT_ROOT / "Assets" / "Video"
VIDEO_WIKILINK_ROOT = "Projects/AlgoTrading/Assets/Video"

DATE_SESSION_RE = re.compile(r"\b\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}\b")

PATTERN_BULLET_TIME = re.compile(r"^(\s*[-*]\s*)\[(\d{2}:\d{2}:\d{2})\](\s*)", re.M)
PATTERN_BOLD_PAREN_TIME = re.compile(r"\*\*\((\d{2}:\d{2}:\d{2})\)\*\*")
PATTERN_SCREENSHOT_TIME = re.compile(r"Скриншот (\d{2}:\d{2}:\d{2})")
PATTERN_VIDEO_URI_PLACEHOLDER = re.compile(r"\[VIDEO_FILE_URI\]#t=(\d{2}:\d{2}:\d{2})")
PATTERN_AT_TIME = re.compile(r"(@\s*)(\d{2}:\d{2}:\d{2})(\s*:)")


@dataclass
class FileResult:
    path: str
    session_id: Optional[str]
    changed: bool
    replacements: Dict[str, int]


def ts_to_seconds(ts: str) -> int:
    h, m, s = map(int, ts.split(":"))
    return h * 3600 + m * 60 + s


def make_time_link(session_id: str, ts: str) -> str:
    return f"[[{VIDEO_WIKILINK_ROOT}/{session_id}.mp4#t={ts}|{ts}]]"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_session_id(path: Path, text: str) -> Optional[str]:
    m = re.search(r'^\s*session_id:\s*"([^"]+)"\s*$', text, re.M)
    if m:
        return m.group(1)

    stem = path.stem
    if DATE_SESSION_RE.fullmatch(stem):
        return stem

    m = re.search(r"Video File:\s*\[\[Projects/AlgoTrading/Assets/Video/([^\]]+)\.mp4\]\]", text)
    if m:
        return m.group(1)

    m = re.search(r"\*\*(\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2})\*\*", text)
    if m:
        return m.group(1)

    m = DATE_SESSION_RE.search(text)
    if m:
        return m.group(0)

    return None


def collect_target_files() -> List[Path]:
    targets: List[Path] = []
    for path in PROJECT_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if (
            PATTERN_BULLET_TIME.search(text)
            or PATTERN_BOLD_PAREN_TIME.search(text)
            or PATTERN_VIDEO_URI_PLACEHOLDER.search(text)
            or PATTERN_SCREENSHOT_TIME.search(text)
            or PATTERN_AT_TIME.search(text)
        ):
            targets.append(path)
    return sorted(targets)


def rewrite_file(path: Path) -> FileResult:
    original = path.read_text(encoding="utf-8")
    session_id = detect_session_id(path, original)

    replacements = {
        "bullet_timecodes": 0,
        "bold_parenthesized_timecodes": 0,
        "screenshot_timecodes": 0,
        "video_uri_placeholders": 0,
        "at_timecodes": 0,
    }

    if not session_id:
        return FileResult(str(path), None, False, replacements)

    def repl_bullet(match: re.Match[str]) -> str:
        replacements["bullet_timecodes"] += 1
        prefix, ts, suffix = match.groups()
        return f"{prefix}{make_time_link(session_id, ts)}{suffix}"

    def repl_bold(match: re.Match[str]) -> str:
        replacements["bold_parenthesized_timecodes"] += 1
        ts = match.group(1)
        return make_time_link(session_id, ts)

    def repl_screenshot(match: re.Match[str]) -> str:
        replacements["screenshot_timecodes"] += 1
        ts = match.group(1)
        return f"Скриншот {make_time_link(session_id, ts)}"

    def repl_video_uri(match: re.Match[str]) -> str:
        replacements["video_uri_placeholders"] += 1
        ts = match.group(1)
        return make_time_link(session_id, ts)

    def repl_at_time(match: re.Match[str]) -> str:
        replacements["at_timecodes"] += 1
        prefix, ts, suffix = match.groups()
        return f"{prefix}{make_time_link(session_id, ts)}{suffix}"

    updated = PATTERN_BULLET_TIME.sub(repl_bullet, original)
    updated = PATTERN_BOLD_PAREN_TIME.sub(repl_bold, updated)
    updated = PATTERN_SCREENSHOT_TIME.sub(repl_screenshot, updated)
    updated = PATTERN_VIDEO_URI_PLACEHOLDER.sub(repl_video_uri, updated)
    updated = PATTERN_AT_TIME.sub(repl_at_time, updated)

    changed = updated != original
    if changed:
        path.write_text(updated, encoding="utf-8")

    return FileResult(str(path), session_id, changed, replacements)


def ensure_video_hardlinks(session_ids: Set[str]) -> Dict[str, List[str]]:
    VIDEO_TARGET_DIR.mkdir(parents=True, exist_ok=True)

    created: List[str] = []
    already_ok: List[str] = []
    replaced_as_hardlink: List[str] = []
    missing_source: List[str] = []
    conflicts: List[str] = []

    for session_id in sorted(session_ids):
        src = VIDEO_SOURCE_ROOT / f"{session_id}.mp4"
        dst = VIDEO_TARGET_DIR / f"{session_id}.mp4"

        if not src.exists():
            missing_source.append(str(src))
            continue

        if dst.exists():
            try:
                if os.path.samefile(src, dst):
                    already_ok.append(str(dst))
                    continue
            except OSError:
                pass

            # Existing file: replace with hardlink only if content is identical.
            if file_sha256(src) == file_sha256(dst):
                dst.unlink()
                os.link(src, dst)
                replaced_as_hardlink.append(str(dst))
            else:
                conflicts.append(str(dst))
            continue

        os.link(src, dst)
        created.append(str(dst))

    return {
        "created": created,
        "already_ok": already_ok,
        "replaced_as_hardlink": replaced_as_hardlink,
        "missing_source": missing_source,
        "conflicts": conflicts,
    }


def main() -> None:
    targets = collect_target_files()
    file_results: List[FileResult] = []
    sessions: Set[str] = set()
    unresolved_files: List[str] = []

    for path in targets:
        result = rewrite_file(path)
        file_results.append(result)
        if result.session_id:
            sessions.add(result.session_id)
        else:
            unresolved_files.append(result.path)

    hardlinks = ensure_video_hardlinks(sessions)

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "video_source_root": str(VIDEO_SOURCE_ROOT),
        "video_target_dir": str(VIDEO_TARGET_DIR),
        "files_scanned": len(targets),
        "files_changed": sum(1 for r in file_results if r.changed),
        "session_ids": sorted(sessions),
        "unresolved_files": unresolved_files,
        "hardlinks": hardlinks,
        "file_results": [asdict(r) for r in file_results],
    }

    reports_dir = PROJECT_ROOT / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"timecode_linkify_report_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "files_scanned": report["files_scanned"],
        "files_changed": report["files_changed"],
        "sessions": len(sessions),
        "hardlinks_created": len(hardlinks["created"]),
        "hardlinks_already_ok": len(hardlinks["already_ok"]),
        "hardlinks_replaced": len(hardlinks["replaced_as_hardlink"]),
        "missing_source": len(hardlinks["missing_source"]),
        "conflicts": len(hardlinks["conflicts"]),
        "unresolved_files": len(unresolved_files),
        "report_path": str(report_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
