from __future__ import annotations

import argparse
import os
from typing import Sequence

from agent_memory_client import memory_write_file
from cli_cmd_algotrading import add_algotrading_parsers
from cli_cmd_agents import _cmd_agents_list, _cmd_agents_status
from cli_cmd_git import _cmd_git_bootstrap_ignore, _cmd_remotes, _cmd_report, _cmd_status
from cli_cmd_hygiene import _cmd_hygiene
from cli_cmd_localai import _cmd_localai_assistant, _cmd_localai_list
from cli_cmd_misc import (
    _cmd_chains_list,
    _cmd_chains_plan,
    _cmd_diagnostics,
    _cmd_doctor,
    _cmd_exec,
    _cmd_preflight,
    _cmd_registry_list,
    _cmd_rg,
)
from cli_cmd_projects import _cmd_projects_info, _cmd_projects_list
from cli_cmd_run import _cmd_run
from cli_env import default_roots
from cli_incidents import add_incidents_parsers
from cli_perf import add_perf_parsers
from cli_quality import add_quality_parsers
from cli_workflow import add_workflow_parsers
from services_preflight import default_lm_studio_base_url, wait_ready
from utils import _load_global_gitignore, _run_capture

__all__ = [
    "default_roots",
    "memory_write_file",
    "run",
    "wait_ready",
    "_load_global_gitignore",
    "_run_capture",
]


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
    plist.add_argument("--json", action="store_true")
    plist.set_defaults(func=_cmd_projects_list)

    pscan = projects_sub.add_parser("scan")
    pscan.add_argument("--roots", nargs="*", default=None)
    pscan.add_argument("--strict-roots", action="store_true")
    pscan.add_argument("--max-depth", type=int, default=3)
    pscan.add_argument("--project", default=None)
    pscan.add_argument("--limit", type=int, default=None)
    pscan.add_argument("--json", action="store_true")
    pscan.set_defaults(func=_cmd_projects_list)

    pinfo = projects_sub.add_parser("info")
    pinfo.add_argument("--roots", nargs="*", default=None)
    pinfo.add_argument("--strict-roots", action="store_true")
    pinfo.add_argument("--max-depth", type=int, default=3)
    pinfo.add_argument("--project", default=None)
    pinfo.add_argument("--limit", type=int, default=None)
    pinfo.add_argument("--json", action="store_true")
    pinfo.set_defaults(func=_cmd_projects_info)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--rag-cwd", default=r"C:\LocalAI\assistant")
    preflight.add_argument("--rag-base-url", default="http://127.0.0.1:8011")
    preflight.add_argument("--lm-base-url", default=default_lm_studio_base_url())
    preflight.add_argument("--check-only", action="store_true")
    preflight.add_argument("--json", action="store_true")
    preflight.set_defaults(func=_cmd_preflight)

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
    astatus.add_argument("--explain", action="store_true")
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
    report.add_argument("--format", choices=["tsv", "jsonl", "md"], default="tsv")
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

    rgp = sub.add_parser("rg")
    rgp.add_argument("--cwd", default=".")
    rgp.add_argument("--no-defaults", action="store_true")
    rgp.add_argument("args", nargs=argparse.REMAINDER)
    rgp.set_defaults(func=_cmd_rg)

    execp = sub.add_parser("exec")
    execp.add_argument("--cwd", required=True)
    execp.add_argument("command", nargs=argparse.REMAINDER)
    execp.set_defaults(func=_cmd_exec)

    hygiene = sub.add_parser("hygiene")
    hygiene.add_argument("--roots", nargs="*", default=None)
    hygiene.add_argument("--strict-roots", action="store_true")
    hygiene.add_argument("--max-depth", type=int, default=3)
    hygiene.add_argument("--project", default=None)
    hygiene.add_argument("--limit", type=int, default=None)
    hygiene.add_argument("--dry-run", action="store_true")
    hygiene.add_argument("--apply", action="store_true")
    hygiene.add_argument("--json", action="store_true")
    hygiene.set_defaults(func=_cmd_hygiene)

    add_quality_parsers(sub)
    add_workflow_parsers(sub)
    add_perf_parsers(sub)
    add_incidents_parsers(sub)
    add_algotrading_parsers(sub)

    return parser


def run(argv: Sequence[str]) -> int:
    argv_list = list(argv)
    prog = _default_prog(argv_list[0] if argv_list else "")
    parser = _build_parser(prog=prog)
    args = parser.parse_args(argv_list[1:])
    return int(args.func(args))
