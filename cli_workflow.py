from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from agent_memory_client import HttpResult, memory_write_file
from cli_env import _diagnostics_rows, default_roots
from cli_parallel import _map_git_projects
from cli_select import _abort_if_roots_invalid, _projects_from_args
from git_ops import _git_origin_url, _normalize_github
from scan import _project_kind
from utils import _print_json, _print_tab, _write_text_atomic


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _write_text_atomic(path, text, backup=True)


def _write_text(path: Path, text: str) -> None:
    if text and not text.endswith("\n"):
        text += "\n"
    _write_text_atomic(path, text, backup=True)


def _http_results_summary(results: list[HttpResult]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    any_failed = False
    for r in results:
        ok = 200 <= int(r.status) < 300
        if not ok:
            any_failed = True
        record_id = ""
        if isinstance(r.json, dict):
            record_id = str(r.json.get("record", {}).get("id", "") or "")
        items.append({"status": int(r.status), "ok": ok, "record_id": record_id})
    return {"count": len(items), "any_failed": any_failed, "items": items}


def _projects_report(args: argparse.Namespace) -> list[dict[str, Any]]:
    projects = _projects_from_args(args)
    jobs = max(1, int(args.jobs))
    results = _map_git_projects(projects, jobs, args.limit, lambda prj: _git_origin_url(prj.path))
    rows: list[dict[str, Any]] = []
    for p, remote in results:
        github = _normalize_github(remote)
        rows.append(
            {
                "name": p.name,
                "path": str(p.path),
                "kind": _project_kind(p.path),
                "remote": remote,
                "github": github,
            }
        )
    return rows


def _cmd_workflow_preflight_memory_report(args: argparse.Namespace) -> int:
    if _abort_if_roots_invalid(args):
        return 2

    roots = [Path(p) for p in args.roots] if args.roots else default_roots()
    diag_rows = _diagnostics_rows(roots)
    problems = [row for row in diag_rows if row.get("status") != "ok"]

    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or f"workflow_preflight_memory_report_{_timestamp()}"
    summary_path = reports_dir / f"{prefix}.summary.json"
    report_path = reports_dir / f"{prefix}.projects.json"
    errors_path = reports_dir / f"{prefix}.errors.log"

    errors: list[str] = []
    memory_summary: dict[str, Any] = {"count": 0, "any_failed": False, "items": []}
    if args.content_file:
        try:
            results = memory_write_file(
                args.base_url,
                args.summary,
                args.content_file,
                auth_token=args.auth_token,
                kind=args.kind,
                tags=args.tags,
                source=args.source,
                author=args.author,
                module=args.module,
                chunk_size=int(args.chunk_size),
            )
            memory_summary = _http_results_summary(results)
        except Exception as e:
            errors.append(f"memory_write_error: {e}")
            memory_summary = {"count": 0, "any_failed": True, "items": []}
    else:
        errors.append("memory_write_error: --content-file is required")
        memory_summary = {"count": 0, "any_failed": True, "items": []}

    project_rows: list[dict[str, Any]] = []
    try:
        project_rows = _projects_report(args)
    except Exception as e:
        errors.append(f"report_error: {e}")

    payload: dict[str, Any] = {
        "kind": "workflow_preflight_memory_report",
        "cwd": os.getcwd(),
        "preflight": {"roots": [str(r) for r in roots], "problems": problems},
        "memory_write": memory_summary,
        "report": {"count": len(project_rows)},
        "artifacts": {
            "summary_json": str(summary_path),
            "projects_json": str(report_path),
            "errors_log": str(errors_path),
        },
    }

    _write_json(summary_path, payload)
    _write_json(report_path, {"projects": project_rows})
    _write_text(errors_path, "\n".join(errors))

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["preflight_problems", str(len(problems))])
        _print_tab(["memory_write_count", str(memory_summary.get("count", 0))])
        _print_tab(["memory_write_failed", str(int(bool(memory_summary.get("any_failed"))))])
        _print_tab(["projects_count", str(len(project_rows))])
        _print_tab(["summary_json", str(summary_path)])
        _print_tab(["projects_json", str(report_path)])
        _print_tab(["errors_log", str(errors_path)])

    any_failed = bool(problems) or bool(memory_summary.get("any_failed")) or bool(errors)
    return 1 if any_failed else 0


def add_workflow_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    wf = sub.add_parser("workflow")
    wf_sub = wf.add_subparsers(dest="workflow_cmd", required=True)

    flow = wf_sub.add_parser("preflight-memory-report")
    flow.add_argument("--roots", nargs="*", default=None)
    flow.add_argument("--strict-roots", action="store_true")
    flow.add_argument("--max-depth", type=int, default=3)
    flow.add_argument("--jobs", type=int, default=16)
    flow.add_argument("--project", default=None)
    flow.add_argument("--limit", type=int, default=None)

    flow.add_argument("--reports-dir", default="reports")
    flow.add_argument("--prefix", default=None)
    flow.add_argument("--json", action="store_true")

    flow.add_argument("--base-url", default="http://127.0.0.1:8011")
    flow.add_argument("--auth-token", default=None)
    flow.add_argument("--content-file", default=None)
    flow.add_argument("--summary", default="workflow memory write")
    flow.add_argument("--kind", default="event")
    flow.add_argument("--tags", nargs="*", default=[])
    flow.add_argument("--source", default=None)
    flow.add_argument("--author", default=None)
    flow.add_argument("--module", default="integrator")
    flow.add_argument("--chunk-size", type=int, default=20000)

    flow.set_defaults(func=_cmd_workflow_preflight_memory_report)
