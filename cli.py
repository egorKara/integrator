from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from agent_memory_client import memory_write_file
from agents_ops import _agent_fix_hints, _agent_project_type, _build_agent_row, _problem_tags
from chains import chain_rows, load_chains
from cli_env import (
    _diagnostics_rows,
    _print_python_status,
    _print_root_status,
    _print_tool_status,
    default_roots,
)
from cli_quality import add_quality_parsers
from cli_parallel import _agent_projects, _map_git_projects, _parallel_map
from cli_select import _abort_if_roots_invalid, _projects_from_args, _projects_from_root
from git_ops import _git_origin_url, _git_status, _git_status_fields, _normalize_github
from registry import load_registry, registry_rows
from run_ops import _resolve_python_command, plan_preset_commands
from scan import Project, _project_kind, _row_sort_key
from cli_workflow import add_workflow_parsers
from utils import (
    _apply_gitignore_lines,
    _apply_limit,
    _ensure_dir_exists,
    _ensure_file_exists,
    _load_global_gitignore,
    _print_json,
    _print_tab,
    _run_command,
    _run_capture,
    _write_stream,
)


def _print_project_list(projects: Sequence[Project]) -> None:
    for project in projects:
        _print_tab([project.name, project.path])


def _cmd_projects_list(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)
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


def _cmd_status(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    any_failed = False

    jobs = max(1, int(args.jobs))
    results = [
        (p, gs)
        for p, gs in _map_git_projects(projects, jobs, args.limit, lambda prj: _git_status(prj.path))
        if gs
    ]
    for p, gs in results:
        if args.only_dirty and gs.clean:
            continue

        fields = _git_status_fields(gs)
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
        if not remote:
            continue
        github = _normalize_github(remote)
        if args.only_github and not github:
            continue
        if args.json:
            payload = {"name": project.name, "path": str(project.path), "remote": remote, "github": github}
            _print_json(payload)
        else:
            _print_tab([project.name, project.path, remote, github])
        if not github:
            any_failed = True
    return 1 if any_failed else 0


def _cmd_doctor(_: argparse.Namespace) -> int:
    _print_tool_status("git")
    _print_python_status()
    _print_root_status(Path(r"C:\vault\Projects"))
    _print_root_status(Path(r"C:\LocalAI"))
    return 0


def _cmd_diagnostics(args: argparse.Namespace) -> int:
    roots = [Path(p) for p in args.roots] if args.roots else default_roots()
    rows = _diagnostics_rows(roots)
    if args.only_problems:
        rows = [row for row in rows if row.get("status") != "ok"]

    any_failed = any(row.get("status") != "ok" for row in rows)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            _print_tab([row["kind"], row["name"], row["status"], row["path"]])
    return 1 if any_failed else 0


def _cmd_exec(args: argparse.Namespace) -> int:
    if not args.command:
        print("command is required", file=sys.stderr)
        return 2
    cwd = Path(args.cwd)
    return _run_command(args.command, cwd)


def _cmd_registry_list(args: argparse.Namespace) -> int:
    path = Path(args.registry).resolve() if args.registry else None
    entries = load_registry(path)
    rows = registry_rows(entries)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            tags_value = row.get("tags", [])
            tags_list = tags_value if isinstance(tags_value, list) else []
            _print_tab(
                [
                    row.get("name", ""),
                    row.get("root", ""),
                    row.get("status", ""),
                    row.get("priority", ""),
                    row.get("entrypoint", ""),
                    ",".join([str(item) for item in tags_list if str(item)]),
                ]
            )
    return 0


def _cmd_chains_list(args: argparse.Namespace) -> int:
    path = Path(args.chains).resolve() if args.chains else None
    chains = load_chains(path)
    rows = chain_rows(chains)
    for row in rows:
        if args.json:
            _print_json(row)
        else:
            steps_value = row.get("steps", [])
            steps_list = steps_value if isinstance(steps_value, list) else []
            _print_tab(
                [
                    row.get("name", ""),
                    row.get("description", ""),
                    str(len(steps_list)),
                ]
            )
    return 0


def _cmd_chains_plan(args: argparse.Namespace) -> int:
    path = Path(args.chains).resolve() if args.chains else None
    chains = load_chains(path)
    chain = next((item for item in chains if item.name == args.name), None)
    if not chain:
        print("chain not found", file=sys.stderr)
        return 2
    steps = [list(step) for step in chain.steps]
    if args.json:
        _print_json({"name": chain.name, "description": chain.description, "steps": steps})
    else:
        _print_tab([chain.name, chain.description])
        for step in steps:
            print("  " + " ".join(step))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    preset = str(args.preset)
    any_failed = False

    if args.json_strict and not args.json:
        print("--json-strict requires --json", file=sys.stderr)
        return 2

    if args.cwd:
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
                code, out, err = _run_capture(cmd, p.path)
                _write_stream(sys.stderr, out)
                _write_stream(sys.stderr, err)
            else:
                code = _run_command(cmd, p.path)
            if code != 0:
                any_failed = True
                if not args.continue_on_error:
                    return 1

    return 1 if any_failed else 0


def _cmd_localai_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects = _projects_from_root(root, max_depth=args.max_depth, needle=args.project)
    projects = _apply_limit(projects, args.limit)
    _print_project_list(projects)
    return 0


def _cmd_localai_assistant(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve() if args.cwd else Path(r"C:\LocalAI\assistant")
    recipe = str(args.recipe)

    if recipe == "memory-write":
        base_url = str(args.base_url or "").strip()
        content_path = str(args.content_file or "").strip()
        summary = str(args.summary or "").strip()
        if not summary:
            summary = Path(content_path).name if content_path else ""
        if not base_url:
            print("base_url required", file=sys.stderr)
            return 2
        if not content_path:
            print("content_file required", file=sys.stderr)
            return 2
        if not Path(content_path).exists():
            print(f"content_file missing: {content_path}", file=sys.stderr)
            return 2

        token = str(args.auth_token or "").strip() or None
        tags = [str(t) for t in (args.tags or []) if str(t).strip()]
        results = memory_write_file(
            base_url,
            summary=summary,
            content_path=content_path,
            auth_token=token,
            chunk_size=int(args.chunk_size),
            kind=str(args.kind or "event"),
            tags=tags,
            source=str(args.source or "") or None,
            author=str(args.author or "") or None,
            module=str(args.module or "") or None,
        )
        ok = all(200 <= r.status < 300 for r in results)
        if args.json:
            for r in results:
                _print_json({"ok": 200 <= r.status < 300, "status": r.status, "json": r.json})
        else:
            for r in results:
                status = "ok" if 200 <= r.status < 300 else "error"
                rec_id = ""
                if isinstance(r.json, dict):
                    rec = r.json.get("record") if isinstance(r.json.get("record"), dict) else None
                    if rec and "id" in rec:
                        rec_id = str(rec["id"])
                _print_tab([status, r.status, rec_id])
        return 0 if ok else 1

    if recipe == "mcp":
        python_cmd = _resolve_python_command(cwd)
        if not python_cmd:
            print("python not found", file=sys.stderr)
            return 2
        target = cwd / "mcp_server.py"
        cmd = [python_cmd, "mcp_server.py"]
    elif recipe == "rag":
        python_cmd = _resolve_python_command(cwd)
        if not python_cmd:
            print("python not found", file=sys.stderr)
            return 2
        target = cwd / "rag_server.py"
        cmd = [python_cmd, "rag_server.py"]
    elif recipe == "reindex":
        target = cwd / "reindex.ps1"
        cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "reindex.ps1"]
    elif recipe == "smoke":
        target = cwd / "Smoke-Test.ps1"
        cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "Smoke-Test.ps1"]
    else:
        print(f"unknown recipe: {recipe}", file=sys.stderr)
        return 2

    if not _ensure_dir_exists(cwd, "cwd"):
        return 2
    if not _ensure_file_exists(target, "recipe target"):
        return 2

    if args.daemon:
        try:
            subprocess.Popen(cmd, cwd=str(cwd))
        except FileNotFoundError:
            print(f"tool not found: {cmd[0]}", file=sys.stderr)
            return 127
        return 0
    return _run_command(cmd, cwd)


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

    rows = [row for _, row in _parallel_map(projects, _build_agent_row, jobs)]
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


def _cmd_report(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    jobs = max(1, int(args.jobs))
    results = _map_git_projects(projects, jobs, args.limit, lambda prj: _git_origin_url(prj.path))
    for p, remote in results:
        github = _normalize_github(remote)
        kind = _project_kind(p.path)
        row = {
            "name": p.name,
            "path": str(p.path),
            "kind": kind,
            "remote": remote,
            "github": github,
        }
        if args.json:
            _print_json(row)
        else:
            _print_tab([row["name"], row["path"], row["kind"], row["remote"], row["github"]])
    return 0


def _cmd_git_bootstrap_ignore(args: argparse.Namespace) -> int:
    projects = _projects_from_args(args)
    if _abort_if_roots_invalid(args):
        return 2
    projects = _apply_limit(projects, args.limit)
    entries = _load_global_gitignore()
    if not entries:
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


def _default_prog(argv0: str) -> str:
    return "integrator"


def _build_parser(prog: str) -> argparse.ArgumentParser:
    from version import __version__

    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("-v", "--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=_cmd_doctor)

    diag = sub.add_parser("diagnostics")
    diag.add_argument("--roots", nargs="*", default=None)
    diag.add_argument("--only-problems", action="store_true")
    diag.add_argument("--json", action="store_true")
    diag.set_defaults(func=_cmd_diagnostics)

    projects = sub.add_parser("projects")
    projects_sub = projects.add_subparsers(dest="projects_cmd", required=True)

    plist = projects_sub.add_parser("list")
    plist.add_argument("--roots", nargs="*", default=None)
    plist.add_argument("--strict-roots", action="store_true")
    plist.add_argument("--max-depth", type=int, default=3)
    plist.add_argument("--project", default=None)
    plist.add_argument("--limit", type=int, default=None)
    plist.set_defaults(func=_cmd_projects_list)

    pscan = projects_sub.add_parser("scan")
    pscan.add_argument("--roots", nargs="*", default=None)
    pscan.add_argument("--strict-roots", action="store_true")
    pscan.add_argument("--max-depth", type=int, default=3)
    pscan.add_argument("--project", default=None)
    pscan.add_argument("--limit", type=int, default=None)
    pscan.set_defaults(func=_cmd_projects_list)

    pinfo = projects_sub.add_parser("info")
    pinfo.add_argument("--roots", nargs="*", default=None)
    pinfo.add_argument("--strict-roots", action="store_true")
    pinfo.add_argument("--max-depth", type=int, default=3)
    pinfo.add_argument("--project", default=None)
    pinfo.add_argument("--limit", type=int, default=None)
    pinfo.add_argument("--json", action="store_true")
    pinfo.set_defaults(func=_cmd_projects_info)

    status = sub.add_parser("status")
    status.add_argument("--roots", nargs="*", default=None)
    status.add_argument("--strict-roots", action="store_true")
    status.add_argument("--max-depth", type=int, default=3)
    status.add_argument("--jobs", type=int, default=min(16, (os.cpu_count() or 4) * 2))
    status.add_argument("--project", default=None)
    status.add_argument("--limit", type=int, default=None)
    status.add_argument("--only-dirty", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=_cmd_status)

    remotes = sub.add_parser("remotes")
    remotes.add_argument("--roots", nargs="*", default=None)
    remotes.add_argument("--strict-roots", action="store_true")
    remotes.add_argument("--max-depth", type=int, default=3)
    remotes.add_argument("--jobs", type=int, default=min(16, (os.cpu_count() or 4) * 2))
    remotes.add_argument("--project", default=None)
    remotes.add_argument("--limit", type=int, default=None)
    remotes.add_argument("--only-github", action="store_true")
    remotes.add_argument("--json", action="store_true")
    remotes.set_defaults(func=_cmd_remotes)

    runp = sub.add_parser("run")
    runp.add_argument("preset", choices=["lint", "test", "build"])
    runp.add_argument("--roots", nargs="*", default=None)
    runp.add_argument("--strict-roots", action="store_true")
    runp.add_argument("--max-depth", type=int, default=3)
    runp.add_argument("--project", default=None)
    runp.add_argument("--cwd", default=None)
    runp.add_argument("--continue-on-error", action="store_true")
    runp.add_argument("--dry-run", action="store_true")
    runp.add_argument("--json", action="store_true")
    runp.add_argument("--json-strict", action="store_true")
    runp.add_argument("--require-clean", action="store_true")
    runp.set_defaults(func=_cmd_run)

    agents = sub.add_parser("agents")
    agents_sub = agents.add_subparsers(dest="agents_cmd", required=True)

    alist = agents_sub.add_parser("list")
    alist.add_argument("--roots", nargs="*", default=None)
    alist.add_argument("--strict-roots", action="store_true")
    alist.add_argument("--max-depth", type=int, default=4)
    alist.add_argument("--project", default=None)
    alist.add_argument("--limit", type=int, default=None)
    alist.add_argument("--json", action="store_true")
    alist.set_defaults(func=_cmd_agents_list)

    astatus = agents_sub.add_parser("status")
    astatus.add_argument("--roots", nargs="*", default=None)
    astatus.add_argument("--strict-roots", action="store_true")
    astatus.add_argument("--max-depth", type=int, default=4)
    astatus.add_argument("--jobs", type=int, default=min(16, (os.cpu_count() or 4) * 2))
    astatus.add_argument("--project", default=None)
    astatus.add_argument("--limit", type=int, default=None)
    astatus.add_argument("--json", action="store_true")
    astatus.add_argument("--only-problems", action="store_true")
    astatus.add_argument("--fix-hints", action="store_true")
    astatus.set_defaults(func=_cmd_agents_status)

    localai = sub.add_parser("localai")
    localai_sub = localai.add_subparsers(dest="localai_cmd", required=True)

    llist = localai_sub.add_parser("list")
    llist.add_argument("--root", default=r"C:\LocalAI")
    llist.add_argument("--max-depth", type=int, default=3)
    llist.add_argument("--project", default=None)
    llist.add_argument("--limit", type=int, default=None)
    llist.set_defaults(func=_cmd_localai_list)

    assistant = localai_sub.add_parser("assistant")
    assistant.add_argument("recipe", choices=["mcp", "rag", "reindex", "smoke", "memory-write"])
    assistant.add_argument("--cwd", default=None)
    assistant.add_argument("--daemon", action="store_true")
    assistant.add_argument("--base-url", default="http://127.0.0.1:8011")
    assistant.add_argument("--auth-token", default=None)
    assistant.add_argument("--content-file", default=None)
    assistant.add_argument("--summary", default=None)
    assistant.add_argument("--kind", default="event")
    assistant.add_argument("--tags", nargs="*", default=[])
    assistant.add_argument("--source", default=None)
    assistant.add_argument("--author", default=None)
    assistant.add_argument("--module", default="integrator")
    assistant.add_argument("--chunk-size", type=int, default=20000)
    assistant.add_argument("--json", action="store_true")
    assistant.set_defaults(func=_cmd_localai_assistant)

    report = sub.add_parser("report")
    report.add_argument("--roots", nargs="*", default=None)
    report.add_argument("--strict-roots", action="store_true")
    report.add_argument("--max-depth", type=int, default=3)
    report.add_argument("--jobs", type=int, default=min(16, (os.cpu_count() or 4) * 2))
    report.add_argument("--project", default=None)
    report.add_argument("--limit", type=int, default=None)
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=_cmd_report)

    chains = sub.add_parser("chains")
    chains_sub = chains.add_subparsers(dest="chains_cmd", required=True)

    clist = chains_sub.add_parser("list")
    clist.add_argument("--chains", default=None)
    clist.add_argument("--json", action="store_true")
    clist.set_defaults(func=_cmd_chains_list)

    cplan = chains_sub.add_parser("plan")
    cplan.add_argument("name")
    cplan.add_argument("--chains", default=None)
    cplan.add_argument("--json", action="store_true")
    cplan.set_defaults(func=_cmd_chains_plan)

    registry = sub.add_parser("registry")
    registry_sub = registry.add_subparsers(dest="registry_cmd", required=True)

    rlist = registry_sub.add_parser("list")
    rlist.add_argument("--registry", default=None)
    rlist.add_argument("--json", action="store_true")
    rlist.set_defaults(func=_cmd_registry_list)

    gitp = sub.add_parser("git")
    git_sub = gitp.add_subparsers(dest="git_cmd", required=True)

    gboot = git_sub.add_parser("bootstrap-ignore")
    gboot.add_argument("--roots", nargs="*", default=None)
    gboot.add_argument("--strict-roots", action="store_true")
    gboot.add_argument("--max-depth", type=int, default=3)
    gboot.add_argument("--project", default=None)
    gboot.add_argument("--limit", type=int, default=None)
    gboot.add_argument("--dry-run", action="store_true")
    gboot.add_argument("--json", action="store_true")
    gboot.set_defaults(func=_cmd_git_bootstrap_ignore)

    execp = sub.add_parser("exec")
    execp.add_argument("--cwd", required=True)
    execp.add_argument("command", nargs=argparse.REMAINDER)
    execp.set_defaults(func=_cmd_exec)

    add_quality_parsers(sub)
    add_workflow_parsers(sub)

    return parser


def run(argv: Sequence[str]) -> int:
    argv_list = list(argv)
    prog = _default_prog(argv_list[0] if argv_list else "")
    parser = _build_parser(prog=prog)
    args = parser.parse_args(argv_list[1:])
    return int(args.func(args))
