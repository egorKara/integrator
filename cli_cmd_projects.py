from __future__ import annotations

import argparse
from typing import Sequence

from cli_select import _abort_if_roots_invalid, _projects_from_args
from scan import Project, _project_kind
from utils import _apply_limit, _print_json, _print_tab


def _print_project_list(projects: Sequence[Project]) -> None:
    for project in projects:
        _print_tab([project.name, project.path])


def _cmd_projects_list(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)
    if getattr(args, "json", False):
        for p in projects:
            _print_json({"name": p.name, "path": str(p.path)})
    else:
        _print_project_list(projects)
    return 0


def _cmd_projects_info(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)
    for p in projects:
        kind = _project_kind(p.path)
        has_git = (p.path / ".git").exists()
        if args.json:
            _print_json({"name": p.name, "path": str(p.path), "kind": kind, "git": has_git})
        else:
            _print_tab([p.name, p.path, kind, int(has_git)])
    return 0
