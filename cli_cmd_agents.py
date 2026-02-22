from __future__ import annotations

import argparse

from agents_ops import _agent_fix_hints, _agent_project_type, _build_agent_row, _problem_tags
from cli_parallel import WorkerError, _agent_projects, _parallel_map
from cli_select import _abort_if_roots_invalid, _projects_from_args
from scan import _project_kind, _row_sort_key
from utils import _apply_limit, _print_json, _print_tab


def _cmd_agents_list(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _agent_projects(projects)
    projects = _apply_limit(projects, args.limit)
    for project in projects:
        row = {
            "name": project.name,
            "path": str(project.path),
            "agent_type": _agent_project_type(project.path),
            "kind": _project_kind(project.path),
        }
        if args.json:
            _print_json(row)
        else:
            _print_tab([row["name"], row["path"], row["agent_type"], row["kind"]])
    return 0


def _cmd_agents_status(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _agent_projects(projects)
    jobs = max(1, int(args.jobs))

    raw_rows = _parallel_map(projects, _build_agent_row, jobs)
    rows: list[dict[str, object]] = []
    for p, row in raw_rows:
        if isinstance(row, WorkerError):
            agent_type = _agent_project_type(p.path) or "unknown"
            rows.append(
                {
                    "name": p.name,
                    "path": str(p.path),
                    "agent_type": agent_type,
                    "kind": "agent",
                    "git": bool((p.path / ".git").exists()),
                    "state": "error",
                    "branch": "",
                    "scripts": 0,
                    "config_json": 0,
                    "gateway_base": "",
                    "gateway_up": False,
                    "media_root_exists": False,
                    "work_root_exists": False,
                    "publish_root_exists": False,
                    "problems": ["worker_error"],
                    "error": row.to_text(),
                }
            )
        else:
            rows.append(row)
    rows.sort(key=_row_sort_key)
    if args.only_problems:
        rows = [row for row in rows if row.get("problems")]
    rows = _apply_limit(rows, args.limit)

    for row in rows:
        if args.fix_hints:
            row["fix_hints"] = _agent_fix_hints(row)
        if args.json:
            _print_json(row)
        else:
            fields = [
                row["name"],
                row["path"],
                row["agent_type"],
                row["kind"],
                int(bool(row["git"])),
                row["state"],
                row["branch"],
                row["scripts"],
                row["config_json"],
                row["gateway_base"],
                int(bool(row["gateway_up"])),
                int(bool(row["media_root_exists"])),
                int(bool(row["work_root_exists"])),
                int(bool(row["publish_root_exists"])),
                ",".join(_problem_tags(row)),
            ]
            if args.fix_hints:
                hints_value = row.get("fix_hints", [])
                if isinstance(hints_value, list):
                    fields.append(";".join([str(item) for item in hints_value]))
                else:
                    fields.append("")
            _print_tab(fields)
    return 0

