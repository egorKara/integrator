from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MoveItem:
    source: Path
    destination: Path


@dataclass(frozen=True, slots=True)
class OrganizeReport:
    moved: list[MoveItem]
    skipped: list[str]
    git_add_exit: int | None


def _move_file(src: Path, dest: Path, apply: bool, moved: list[MoveItem], skipped: list[str]) -> None:
    if not src.exists():
        return
    if dest.exists():
        skipped.append(f"exists:{dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if apply:
        shutil.move(str(src), str(dest))
    moved.append(MoveItem(src, dest))


def _git_add(root: Path, apply: bool) -> int | None:
    if not apply:
        return None
    result = subprocess.run(["git", "add", "."], cwd=str(root))
    return int(result.returncode)


def organize(root: Path, apply: bool) -> OrganizeReport:
    moved: list[MoveItem] = []
    skipped: list[str] = []

    root_tests = [
        "test_deps.py",
        "test_knowledge.py",
        "test_numpy.py",
        "test_pipeline_logic.py",
        "test_rag.py",
        "test_st_load.py",
        "test_torch.py",
        "test_transformers.py",
    ]
    for name in root_tests:
        _move_file(root / name, root / "tests" / name, apply, moved, skipped)

    root_debug = [
        "debug_env.py",
    ]
    for name in root_debug:
        _move_file(root / name, root / "scripts" / name, apply, moved, skipped)

    for path in root.glob("debug_*.py"):
        _move_file(path, root / "scripts" / path.name, apply, moved, skipped)

    _move_file(root / "check_health.py", root / "scripts" / "check_health.py", apply, moved, skipped)

    git_add_exit = _git_add(root, apply)
    return OrganizeReport(moved=moved, skipped=skipped, git_add_exit=git_add_exit)


def write_report(report: OrganizeReport, output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Assistant Untracked Organize Report")
    lines.append("")
    lines.append(f"moved: {len(report.moved)}")
    lines.append(f"skipped: {len(report.skipped)}")
    lines.append(f"git_add_exit: {report.git_add_exit if report.git_add_exit is not None else '-'}")
    lines.append("")
    if report.moved:
        lines.append("## moved")
        for item in report.moved:
            lines.append(f"- {item.source} -> {item.destination}")
        lines.append("")
    if report.skipped:
        lines.append("## skipped")
        for skipped_item in report.skipped:
            lines.append(f"- {skipped_item}")
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"C:\LocalAI\assistant")
    ap.add_argument("--output", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        return 2
    report = organize(root, args.apply)
    write_report(report, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
