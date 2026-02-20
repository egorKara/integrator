from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from cli_env import _root_status_lines, default_roots
from scan import Project, _filter_projects, iter_projects


def _roots_from_args(args: argparse.Namespace) -> list[Path]:
    roots = [Path(p) for p in args.roots] if args.roots else default_roots()
    if not getattr(args, "strict_roots", False):
        return roots

    ok_roots, problem_lines = _root_status_lines(roots)
    if problem_lines:
        args._roots_error = True
        for line in problem_lines:
            print(line, file=sys.stderr)
    return ok_roots


def _abort_if_roots_invalid(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "_roots_error", False))


def _projects_from_roots(roots: Sequence[Path], max_depth: int, needle: str | None) -> list[Project]:
    projects = iter_projects(roots, max_depth=max_depth)
    return _filter_projects(projects, needle)


def _projects_from_args(args: argparse.Namespace) -> list[Project]:
    roots = _roots_from_args(args)
    return _projects_from_roots(roots, args.max_depth, args.project)


def _projects_from_root(root: Path, max_depth: int, needle: str | None) -> list[Project]:
    return _projects_from_roots([root], max_depth=max_depth, needle=needle)
