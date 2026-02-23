from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from cli_select import _abort_if_roots_invalid, _projects_from_args
from utils import _apply_limit, _print_json, _print_tab


@dataclass(frozen=True, slots=True)
class HygieneAction:
    project: str
    project_path: Path
    target: Path
    action: str
    reason: str


_FORBIDDEN_PARTS = {".git", ".trae", "docs", "reports", "vault"}


def _is_safe_target(project_root: Path, target: Path, reason: str) -> bool:
    try:
        root = project_root.resolve()
        t = target.resolve()
    except OSError:
        return False

    if root == t:
        return False
    if root not in t.parents:
        return False

    parts = {p.lower() for p in t.parts}
    if any(part in _FORBIDDEN_PARTS for part in parts):
        return False

    name = t.name.lower()
    if reason in {"pycache_root", "pycache_nested"}:
        return name == "__pycache__"
    if reason in {"mypy_cache", "ruff_cache", "pytest_cache", "tox"}:
        return name in {".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox"}
    if reason == "tests_tmp":
        return t.parent.name.lower() == "tests" and name.startswith(".tmp_")
    return False


def _find_actions_for_project(project_root: Path) -> list[HygieneAction]:
    actions: list[HygieneAction] = []
    root = project_root
    name = root.name

    candidates = [
        (root / ".mypy_cache", "delete_dir", "mypy_cache"),
        (root / ".ruff_cache", "delete_dir", "ruff_cache"),
        (root / ".pytest_cache", "delete_dir", "pytest_cache"),
        (root / ".tox", "delete_dir", "tox"),
        (root / "__pycache__", "delete_dir", "pycache_root"),
    ]

    for path, action, reason in candidates:
        if path.exists() and _is_safe_target(root, path, reason):
            actions.append(HygieneAction(name, root, path, action, reason))

    tests_dir = root / "tests"
    if tests_dir.is_dir():
        try:
            for child in tests_dir.iterdir():
                if not child.is_dir():
                    continue
                if child.name.startswith(".tmp_") and _is_safe_target(root, child, "tests_tmp"):
                    actions.append(HygieneAction(name, root, child, "delete_dir", "tests_tmp"))
        except OSError:
            pass

    skip_names = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "dist", "build", ".trae"}
    for current, dirs, _files in os.walk(root):
        cur = Path(current)
        dirs[:] = [d for d in dirs if d not in skip_names]
        for d in list(dirs):
            if d != "__pycache__":
                continue
            target = cur / d
            if _is_safe_target(root, target, "pycache_nested"):
                actions.append(HygieneAction(name, root, target, "delete_dir", "pycache_nested"))

    seen: set[Path] = set()
    ordered: list[HygieneAction] = []
    for act in actions:
        if act.target in seen:
            continue
        seen.add(act.target)
        ordered.append(act)
    ordered.sort(key=lambda a: str(a.target).lower())
    return ordered


def _apply_action(act: HygieneAction) -> tuple[str, str]:
    if act.action == "delete_dir":
        try:
            shutil.rmtree(act.target)
            return "deleted", ""
        except OSError as e:
            return "error", str(e)
    return "skipped", "unknown_action"


def _cmd_hygiene(args: argparse.Namespace) -> int:
    if args.apply and args.dry_run:
        return 2

    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)

    any_failed = False
    mode = "apply" if args.apply else "dry-run"

    for p in projects:
        for act in _find_actions_for_project(p.path):
            status = "planned"
            err = ""
            if args.apply:
                status, err = _apply_action(act)
                if status == "error":
                    any_failed = True
            rel = ""
            try:
                rel = str(act.target.resolve().relative_to(act.project_path.resolve()))
            except Exception:
                rel = str(act.target)

            if args.json:
                payload = {
                    "kind": "hygiene_action",
                    "mode": mode,
                    "project": act.project,
                    "project_path": str(act.project_path),
                    "target": str(act.target),
                    "rel": rel,
                    "action": act.action,
                    "reason": act.reason,
                    "status": status,
                }
                if err:
                    payload["error"] = err
                _print_json(payload)
            else:
                row = [act.project, mode, act.action, act.reason, status, rel]
                _print_tab(row)

    return 1 if any_failed else 0

