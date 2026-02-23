from __future__ import annotations

import argparse

from cli_parallel import WorkerError, _map_git_projects
from cli_select import _abort_if_roots_invalid, _projects_from_args
from git_ops import _git_origin_url, _git_status, _git_status_fields, _normalize_github
from scan import _project_kind
from utils import (
    _apply_gitignore_lines,
    _apply_limit,
    _print_json,
    _print_tab,
)


def _cmd_status(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    any_failed = False

    jobs = max(1, int(args.jobs))
    results = _map_git_projects(projects, jobs, args.limit, lambda prj: _git_status(prj.path))
    for p, gs in results:
        if isinstance(gs, WorkerError):
            fields: dict[str, object] = {
                "state": "error",
                "branch": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "changed": 0,
                "untracked": 0,
            }
        else:
            if not gs:
                continue
            fields = dict(_git_status_fields(gs))

        if args.only_dirty and fields["state"] == "clean":
            continue
        if args.json:
            payload = {"name": p.name, "path": str(p.path), **fields}
            _print_json(payload)
        else:
            _print_tab(
                [
                    p.name,
                    p.path,
                    fields["state"],
                    fields["branch"],
                    fields["upstream"],
                    fields["ahead"],
                    fields["behind"],
                    fields["changed"],
                    fields["untracked"],
                ]
            )

        if fields["state"] in {"error", "tool-missing"}:
            any_failed = True

    return 1 if any_failed else 0


def _cmd_remotes(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    any_failed = False
    jobs = max(1, int(args.jobs))
    results = _map_git_projects(projects, jobs, args.limit, lambda prj: _git_origin_url(prj.path))
    for project, remote in results:
        if isinstance(remote, WorkerError):
            any_failed = True
            remote_value = ""
            github = ""
        else:
            remote_value = remote
            if not remote_value:
                continue
            github = _normalize_github(remote_value)
            if args.only_github and not github:
                continue
        if args.json:
            payload = {"name": project.name, "path": str(project.path), "remote": remote_value, "github": github}
            _print_json(payload)
        else:
            _print_tab([project.name, project.path, remote_value, github])
        if not github:
            any_failed = True
    return 1 if any_failed else 0


def _cmd_report(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    jobs = max(1, int(args.jobs))
    def worker(prj: object):
        assert hasattr(prj, "path")
        remote = _git_origin_url(prj.path)
        gs = _git_status(prj.path)
        fields: dict[str, object] = dict(_git_status_fields(gs)) if gs else {}
        return remote, fields

    results = _map_git_projects(projects, jobs, args.limit, worker)
    format_value = str(getattr(args, "format", "tsv")).strip().lower()
    if args.json:
        format_value = "jsonl"

    def md_escape(s: object) -> str:
        text = str(s)
        return text.replace("|", "\\|").replace("\n", " ").strip()

    if format_value == "md":
        print("| name | path | kind | state | branch | remote | github |")
        print("|---|---|---|---|---|---|---|")
    for p, res in results:
        if isinstance(res, WorkerError):
            remote_value = ""
            fields: dict[str, object] = {
                "state": "error",
                "branch": "",
                "upstream": "",
                "ahead": 0,
                "behind": 0,
                "changed": 0,
                "untracked": 0,
            }
        else:
            remote_value, fields_any = res
            fields = dict(fields_any) if isinstance(fields_any, dict) else {}
            if not fields:
                fields = {
                    "state": "error",
                    "branch": "",
                    "upstream": "",
                    "ahead": 0,
                    "behind": 0,
                    "changed": 0,
                    "untracked": 0,
                }

        github = _normalize_github(remote_value) if remote_value else ""
        kind = _project_kind(p.path)
        row: dict[str, object] = {
            "name": p.name,
            "path": str(p.path),
            "kind": kind,
            "remote": remote_value,
            "github": github,
        }
        if format_value == "jsonl":
            row["git"] = True
            row.update(fields)
            _print_json(row)
        elif format_value == "md":
            state = fields.get("state", "")
            branch = fields.get("branch", "")
            print(
                "| "
                + " | ".join(
                    [
                        md_escape(row["name"]),
                        md_escape(row["path"]),
                        md_escape(row["kind"]),
                        md_escape(state),
                        md_escape(branch),
                        md_escape(row["remote"]),
                        md_escape(row["github"]),
                    ]
                )
                + " |"
            )
        else:
            _print_tab([row["name"], row["path"], row["kind"], row["remote"], row["github"]])
    return 0


def _cmd_git_bootstrap_ignore(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)
    import cli as cli_module

    entries = cli_module._load_global_gitignore()
    if not entries:
        import sys

        print("global_gitignore_localai is empty", file=sys.stderr)
        return 2
    any_failed = False
    for project in projects:
        if not (project.path / ".git").exists():
            continue
        gitignore_path = project.path / ".gitignore"
        updated, missing, error = _apply_gitignore_lines(gitignore_path, entries, args.dry_run)
        payload = {
            "name": project.name,
            "path": str(project.path),
            "updated": updated,
            "missing": missing,
            "error": error or "",
        }
        if args.json:
            _print_json(payload)
        else:
            status = "ok" if not error else "error"
            _print_tab([project.name, project.path, status, int(updated), len(missing)])
        if error:
            any_failed = True
    return 1 if any_failed else 0
