from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Sequence

from registry import load_registry, registry_roots
from utils import _print_kv


def _root_status(root: Path) -> str:
    try:
        if not root.exists():
            return "missing"
    except PermissionError:
        return "access_denied"

    if not root.is_dir():
        return "missing"

    try:
        with os.scandir(root) as it:
            next(it, None)
    except PermissionError:
        return "access_denied"
    except FileNotFoundError:
        return "missing"
    return "ok"


def _root_status_lines(roots: Sequence[Path]) -> tuple[list[Path], list[str]]:
    ok_roots: list[Path] = []
    problem_lines: list[str] = []
    for root in roots:
        status = _root_status(root)
        if status == "ok":
            ok_roots.append(root)
        else:
            problem_lines.append(f"root={root}\tstatus={status}")
    return ok_roots, problem_lines


def _print_root_status(root: Path) -> None:
    status = _root_status(root)
    exists = status == "ok"
    print(f"root={root}\tstatus={status}\texists={exists}")


def _print_tool_status(tool: str) -> None:
    _print_kv(tool, shutil.which(tool) or "")


def _tool_status(tool: str) -> tuple[str, str]:
    path = shutil.which(tool) or ""
    status = "ok" if path else "tool-missing"
    return status, path


def _python_status() -> tuple[str, str]:
    path = sys.executable
    status = "ok" if Path(path).exists() else "tool-missing"
    return status, path


def _print_python_status() -> None:
    _, path = _python_status()
    _print_kv("python", path)


def _diagnostics_rows(roots: Sequence[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    py_status, py_path = _python_status()
    rows.append({"kind": "tool", "name": "python", "path": py_path, "status": py_status})

    for tool in ("git", "node", "npm", "pnpm", "yarn"):
        status, path = _tool_status(tool)
        rows.append({"kind": "tool", "name": tool, "path": path, "status": status})

    for root in roots:
        status = _root_status(root)
        rows.append({"kind": "root", "name": str(root), "path": str(root), "status": status})

    return rows


def default_roots() -> list[Path]:
    env = os.environ.get("INTEGRATOR_ROOTS") or os.environ.get("TAST_ROOTS")
    if env:
        parts = [p.strip() for p in env.split(";") if p.strip()]
        return [Path(p) for p in parts]
    registry_entries = load_registry()
    registry_paths = registry_roots(registry_entries)
    if registry_paths:
        return registry_paths
    return [Path(r"C:\vault\Projects"), Path(r"C:\LocalAI")]
