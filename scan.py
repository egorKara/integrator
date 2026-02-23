from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence


@dataclass(frozen=True, slots=True)
class Project:
    name: str
    path: Path


_MARKER_FILES = (
    "pyproject.toml",
    "setup.cfg",
    "requirements.txt",
    "Pipfile",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    ".sln",
)

_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
}


def _is_agent_project_dir(path: Path) -> bool:
    if (path / ".trae" / "rules" / "project_rules.md").exists():
        return True

    config_dir = path / "config"
    scripts_dir = path / "scripts"
    if not config_dir.is_dir() or not scripts_dir.is_dir():
        return False

    try:
        return any(config_dir.glob("*.json"))
    except PermissionError:
        return False


def _is_vault_dir(path: Path) -> bool:
    if (path / ".obsidian").is_dir():
        return True
    if (path / "KB").is_dir() and (path / "Notes").is_dir():
        return True
    return False


def _is_project_dir(path: Path) -> bool:
    if (path / ".git").exists():
        return True
    if _is_vault_dir(path):
        return True
    for marker in _MARKER_FILES:
        if marker == ".sln":
            if any(path.glob("*.sln")):
                return True
            continue
        if (path / marker).exists():
            return True
    if _is_agent_project_dir(path):
        return True
    return False


def _iter_candidate_dirs(roots: Sequence[Path], max_depth: int) -> Iterator[Path]:
    def iter_children(parent: Path) -> Iterator[Path]:
        try:
            for entry in os.scandir(parent):
                if not entry.is_dir(follow_symlinks=False):
                    continue
                name = entry.name
                if name in _SKIP_DIR_NAMES:
                    continue
                yield Path(entry.path)
        except FileNotFoundError:
            return
        except PermissionError:
            return

    queue: deque[tuple[Path, int]] = deque((root, 0) for root in roots)

    while queue:
        current, depth = queue.popleft()
        yield current
        if depth >= max_depth:
            continue
        for child in iter_children(current):
            queue.append((child, depth + 1))


def iter_projects(roots: Sequence[Path], max_depth: int = 3) -> list[Project]:
    seen: set[Path] = set()
    projects: list[Project] = []
    for candidate in _iter_candidate_dirs(roots, max_depth=max_depth):
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.exists():
            continue
        if _is_project_dir(candidate):
            projects.append(Project(name=candidate.name, path=candidate))
    projects.sort(key=_project_sort_key)
    return projects


def _project_sort_key(project: Project) -> tuple[str, str]:
    return project.name.lower(), str(project.path).lower()


def _row_sort_key(row: dict[str, object]) -> tuple[str, str]:
    return str(row.get("name", "")).lower(), str(row.get("path", "")).lower()


def _filter_projects(projects: list[Project], needle: str | None) -> list[Project]:
    if not needle:
        return projects
    n = needle.lower()
    return [p for p in projects if n in p.name.lower() or n in str(p.path).lower()]


def _has_any(path: Path, names: Sequence[str]) -> bool:
    for name in names:
        if (path / name).exists():
            return True
    return False


def _project_kind(project_dir: Path) -> str:
    if _is_vault_dir(project_dir):
        return "vault"
    if (project_dir / "package.json").exists():
        return "node"
    if (project_dir / "go.mod").exists():
        return "go"
    if (project_dir / "Cargo.toml").exists():
        return "rust"
    if _has_any(project_dir, ("pyproject.toml", "requirements.txt", "Pipfile", "setup.cfg")):
        return "python"
    if _has_any(project_dir, ("pom.xml", "build.gradle", "build.gradle.kts")):
        return "jvm"
    if any(project_dir.glob("*.sln")):
        return "dotnet"
    if _is_agent_project_dir(project_dir):
        return "agent"
    return "unknown"
