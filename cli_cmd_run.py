from __future__ import annotations

import argparse
import sys
from typing import Sequence

from cli_select import _abort_if_roots_invalid, _projects_from_args
from git_ops import _git_status, _git_status_fields
from run_ops import plan_preset_commands
from scan import Project
from utils import _print_json, _print_tab, _run_command, _write_stream


def _preflight_dirty_projects(projects: Sequence[Project]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for project in projects:
        gs = _git_status(project.path)
        if not gs:
            continue
        fields = _git_status_fields(gs)
        if fields["state"] not in {"dirty", "error", "tool-missing"}:
            continue
        rows.append({"name": project.name, "path": str(project.path), **fields})
    return rows


def _cmd_run(args: argparse.Namespace) -> int:
    preset = str(args.preset)
    any_failed = False

    if args.json_strict and not args.json:
        print("--json-strict requires --json", file=sys.stderr)
        return 2

    if args.cwd:
        from pathlib import Path

        cwd_path = Path(args.cwd).resolve()
        targets = [Project(name=cwd_path.name, path=cwd_path)]
    else:
        targets = _projects_from_args(args)
        if _abort_if_roots_invalid(args):
            return 2

        if args.require_clean:
            dirty = _preflight_dirty_projects(targets)
            if dirty:
                for row in dirty:
                    print(
                        "\t".join(
                            [
                                "preflight_dirty",
                                str(row["name"]),
                                str(row["path"]),
                                str(row["state"]),
                                str(row["changed"]),
                                str(row["untracked"]),
                            ]
                        ),
                        file=sys.stderr,
                    )
                return 2

    for p in targets:
        if not p.path.exists():
            continue
        commands = plan_preset_commands(p.path, preset)
        if not commands:
            continue

        if args.json:
            _print_json(
                {
                    "name": p.name,
                    "path": str(p.path),
                    "preset": preset,
                    "commands": commands,
                    "dry_run": bool(args.dry_run),
                }
            )
        else:
            _print_tab([p.name, p.path, preset])
            for cmd in commands:
                print("  " + " ".join(cmd))

        if args.dry_run:
            continue

        for cmd in commands:
            if args.json and args.json_strict:
                import cli as cli_module

                code, out, err = cli_module._run_capture(cmd, p.path)
                _write_stream(sys.stderr, out)
                _write_stream(sys.stderr, err)
            else:
                code = _run_command(cmd, p.path)
            if code != 0:
                any_failed = True
                if not args.continue_on_error:
                    return 1

    return 1 if any_failed else 0
