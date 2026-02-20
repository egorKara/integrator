from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class HygieneResult:
    moved_logs: list[str]
    removed_cache: list[str]
    gitignore_updated: bool
    gitignore_missing: list[str]
    git_add_exit: int | None


DEFAULT_GITIGNORE = [
    ".env",
    ".env.example",
    "__pycache__/",
    "*.pyc",
    "*.err",
    "*.out",
    "*.pid",
]


def _ensure_gitignore(path: Path, entries: list[str], apply: bool) -> tuple[bool, list[str]]:
    if not path.exists():
        if not apply:
            return False, entries
        text = "\n".join(entries) + "\n"
        path.write_text(text, encoding="utf-8")
        return True, entries
    existing = {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
    missing = [entry for entry in entries if entry not in existing]
    if not missing:
        return False, []
    if not apply:
        return False, missing
    text = "\n".join(list(existing) + missing) + "\n"
    path.write_text(text, encoding="utf-8")
    return True, missing


def _move_logs(root: Path, logs_root: Path, apply: bool) -> list[str]:
    target_dir = logs_root / "assistant"
    patterns = ["rag_server.err.*", "rag_server.out.*"]
    moved: list[str] = []
    for pattern in patterns:
        for path in root.glob(pattern):
            dest = target_dir / path.name
            moved.append(str(path))
            if apply:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(dest))
    return moved


def _remove_cache(root: Path, apply: bool) -> list[str]:
    removed: list[str] = []
    for path in root.rglob("__pycache__"):
        removed.append(str(path))
        if apply:
            shutil.rmtree(path, ignore_errors=True)
    for path in root.rglob("*.pyc"):
        removed.append(str(path))
        if apply:
            path.unlink(missing_ok=True)
    return removed


def _git_add(path: Path, apply: bool) -> int | None:
    if not apply:
        return None
    result = subprocess.run(["git", "add", str(path)], cwd=str(path.parent))
    return int(result.returncode)


def run(root: Path, logs_root: Path, apply: bool) -> HygieneResult:
    gitignore_path = root / ".gitignore"
    gitignore_updated, gitignore_missing = _ensure_gitignore(
        gitignore_path, DEFAULT_GITIGNORE, apply
    )
    moved_logs = _move_logs(root, logs_root, apply)
    removed_cache = _remove_cache(root, apply)
    git_add_exit = _git_add(gitignore_path, apply) if gitignore_path.exists() else None
    return HygieneResult(
        moved_logs=moved_logs,
        removed_cache=removed_cache,
        gitignore_updated=gitignore_updated,
        gitignore_missing=gitignore_missing,
        git_add_exit=git_add_exit,
    )


def write_report(result: HygieneResult, output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Assistant Hygiene Report")
    lines.append("")
    lines.append(f"moved_logs: {len(result.moved_logs)}")
    lines.append(f"removed_cache: {len(result.removed_cache)}")
    lines.append(f"gitignore_updated: {result.gitignore_updated}")
    lines.append(f"gitignore_missing: {', '.join(result.gitignore_missing) or '-'}")
    lines.append(f"git_add_exit: {result.git_add_exit if result.git_add_exit is not None else '-'}")
    lines.append("")
    if result.moved_logs:
        lines.append("## moved_logs")
        for item in result.moved_logs:
            lines.append(f"- {item}")
        lines.append("")
    if result.removed_cache:
        lines.append("## removed_cache")
        for item in result.removed_cache:
            lines.append(f"- {item}")
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"C:\LocalAI\assistant")
    ap.add_argument("--logs-root", default=r"C:\LocalAI\logs")
    ap.add_argument("--output", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    logs_root = Path(args.logs_root)
    if not root.exists():
        return 2
    result = run(root, logs_root, args.apply)
    write_report(result, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
