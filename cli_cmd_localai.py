from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cli_env import default_localai_assistant_root
from cli_cmd_projects import _print_project_list
from cli_select import _projects_from_root
from run_ops import _resolve_python_command
from utils import _apply_limit, _ensure_dir_exists, _ensure_file_exists, _print_json, _print_tab, _run_command


def _cmd_localai_list(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    projects = _projects_from_root(root, max_depth=args.max_depth, needle=args.project)
    projects = _apply_limit(projects, args.limit)
    _print_project_list(projects)
    return 0


def _cmd_localai_assistant(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve() if args.cwd else default_localai_assistant_root()
    recipe = str(args.recipe)

    if recipe == "memory-write":
        import cli as cli_module

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
        results = cli_module.memory_write_file(
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
