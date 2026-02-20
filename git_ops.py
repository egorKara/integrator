from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


@dataclass(frozen=True, slots=True)
class GitStatus:
    branch: str
    upstream: str
    ahead: int
    behind: int
    clean: bool
    changed: int
    untracked: int
    raw: str


class GitStatusFields(TypedDict):
    state: str
    branch: str
    upstream: str
    ahead: int
    behind: int
    changed: int
    untracked: int


def _parse_git_branch_line(line: str) -> tuple[str, str, int, int]:
    branch = ""
    upstream = ""
    ahead = 0
    behind = 0

    parts = line.split(" ", 1)
    branch = parts[0].replace("##", "").strip()
    if len(parts) == 1:
        return branch, upstream, ahead, behind
    meta = parts[1].strip()
    if not branch and meta:
        branch = meta.split(" ", 1)[0].strip()

    if "..." in branch:
        branch_part, upstream_part = branch.split("...", 1)
        branch = branch_part.strip()
        upstream = upstream_part.strip()
    elif "..." in meta:
        head, rest = meta.split("...", 1)
        branch = head.strip()
        rest = rest.strip()
        if " " in rest:
            upstream, meta = rest.split(" ", 1)
        else:
            upstream = rest
            meta = ""

    meta = meta.strip()
    if meta.startswith("[") and meta.endswith("]"):
        inside = meta[1:-1].strip()
        for part in [p.strip() for p in inside.split(",") if p.strip()]:
            if part.startswith("ahead "):
                try:
                    ahead = int(part.split(" ", 1)[1])
                except ValueError:
                    ahead = 0
            elif part.startswith("behind "):
                try:
                    behind = int(part.split(" ", 1)[1])
                except ValueError:
                    behind = 0

    return branch, upstream, ahead, behind


def _resolve_git_dir(path: Path) -> Path | None:
    git_entry = path / ".git"
    if git_entry.is_dir():
        return git_entry
    if git_entry.is_file():
        try:
            text = git_entry.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            return None
        first = text.splitlines()[0].strip() if text else ""
        if first.lower().startswith("gitdir:"):
            raw = first.split(":", 1)[1].strip()
            if not raw:
                return None
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = (path / raw).resolve()
            if candidate.exists():
                return candidate
    return None


def _git_status(path: Path) -> GitStatus | None:
    if not (path / ".git").exists():
        return None

    from utils import _run_capture

    git_dir = _resolve_git_dir(path)
    if not git_dir:
        return GitStatus(
            branch="",
            upstream="",
            ahead=0,
            behind=0,
            clean=False,
            changed=0,
            untracked=0,
            raw="invalid .git",
        )

    code, out, err = _run_capture(
        ["git", f"--git-dir={git_dir}", f"--work-tree={path}", "status", "-sb", "--porcelain"],
        cwd=path,
    )
    raw = out.strip("\n")
    err_text = err.strip()
    if code == 127:
        return GitStatus(
            branch="",
            upstream="",
            ahead=0,
            behind=0,
            clean=False,
            changed=0,
            untracked=0,
            raw=err_text or "tool not found: git",
        )
    if code != 0:
        raw_text = raw or err_text
        return GitStatus(
            branch="",
            upstream="",
            ahead=0,
            behind=0,
            clean=False,
            changed=0,
            untracked=0,
            raw=raw_text,
        )

    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return GitStatus(
            branch="",
            upstream="",
            ahead=0,
            behind=0,
            clean=True,
            changed=0,
            untracked=0,
            raw=raw,
        )

    first = lines[0]
    branch, upstream, ahead, behind = _parse_git_branch_line(first)

    clean = len(lines) == 1
    untracked = sum(1 for ln in lines[1:] if ln.startswith("?? "))
    changed = len(lines[1:]) - untracked

    return GitStatus(
        branch=branch,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        clean=clean,
        changed=changed,
        untracked=untracked,
        raw=raw,
    )


def _git_status_fields(gs: GitStatus) -> GitStatusFields:
    state = "clean" if gs.clean else "dirty"
    raw_lower = gs.raw.lower()
    if not gs.clean and raw_lower.startswith("tool not found:"):
        state = "tool-missing"
    elif not gs.clean and gs.branch == "":
        state = "error"
    return {
        "state": state,
        "branch": gs.branch,
        "upstream": gs.upstream,
        "ahead": gs.ahead,
        "behind": gs.behind,
        "changed": gs.changed,
        "untracked": gs.untracked,
    }


def _git_origin_url(path: Path) -> str:
    from utils import _run_capture

    if not (path / ".git").exists():
        return ""

    git_dir = _resolve_git_dir(path)
    if not git_dir:
        return ""

    code, out, _ = _run_capture(
        ["git", f"--git-dir={git_dir}", f"--work-tree={path}", "config", "--get", "remote.origin.url"],
        cwd=path,
    )
    if code != 0:
        return ""
    return out.strip()


def _normalize_github(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if url.startswith("git@github.com:"):
        target = url.replace("git@github.com:", "https://github.com/")
        return target[:-4] if target.endswith(".git") else target
    if url.startswith("https://github.com/"):
        return url[:-4] if url.endswith(".git") else url
    return ""
