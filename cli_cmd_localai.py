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

    routes: dict[str, str] | None = None
    gateway_json = str(args.gateway_json or "").strip()
    if gateway_json:
        from agent_memory_routes import load_gateway_routes

        routes = load_gateway_routes(gateway_json)

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
            routes=routes,
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

    if recipe in {"memory-search", "memory-recent", "memory-retrieve", "memory-stats", "memory-feedback", "task-add", "tasks-pending", "task-close"}:
        from agent_memory_client import (
            memory_feedback,
            memory_recent,
            memory_retrieve,
            memory_search,
            memory_stats,
            memory_write,
        )

        base_url = str(args.base_url or "").strip()
        token = str(args.auth_token or "").strip() or None
        kind_filter = str(args.filter_kind or "").strip() or None
        module_filter = str(args.filter_module or "").strip() or None
        limit = int(args.limit)
        include_quarantined = bool(args.include_quarantined)
        include_deleted = bool(args.include_deleted)
        if not base_url:
            print("base_url required", file=sys.stderr)
            return 2

        if recipe == "tasks-pending":
            pending: list[dict[str, object]] = []
            tasks = memory_search(
                base_url,
                "[TASK]",
                limit=max(10, limit),
                kind="task",
                include_quarantined=include_quarantined,
                include_deleted=include_deleted,
                auth_token=token,
                routes=routes,
            )
            events = memory_search(
                base_url,
                "TaskId:",
                limit=200,
                kind="event",
                include_quarantined=include_quarantined,
                include_deleted=include_deleted,
                auth_token=token,
                routes=routes,
            )
            closed: set[int] = set()
            if isinstance(events.json, dict):
                items = events.json.get("results")
                if isinstance(items, list):
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        content = str(it.get("content") or "")
                        if "Status: done" not in content:
                            continue
                        import re

                        m = re.search(r"TaskId:\s*(\d+)", content)
                        if m:
                            try:
                                closed.add(int(m.group(1)))
                            except Exception:
                                pass
            if isinstance(tasks.json, dict):
                items = tasks.json.get("results")
                if isinstance(items, list):
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        content = str(it.get("content") or "")
                        if "Status: open" not in content:
                            continue
                        tid = it.get("id")
                        try:
                            tid_int = int(tid) if tid is not None else -1
                        except Exception:
                            tid_int = -1
                        if tid_int > 0 and tid_int in closed:
                            continue
                        pending.append(it)
            ok_tasks = 200 <= int(tasks.status) < 300
            ok_events = 200 <= int(events.status) < 300
            ok = ok_tasks and ok_events
            if args.json:
                for it in pending:
                    _print_json({"ok": True, "task": it})
            else:
                for it in pending:
                    _print_tab([it.get("id", ""), it.get("kind", ""), it.get("summary", "")])
            return 0 if ok else 1

        if recipe == "memory-search":
            q = str(args.q or "").strip()
            if not q:
                print("q required", file=sys.stderr)
                return 2
            res = memory_search(
                base_url,
                q,
                limit=limit,
                kind=kind_filter,
                min_importance=args.min_importance,
                include_quarantined=include_quarantined,
                include_deleted=include_deleted,
                auth_token=token,
                routes=routes,
            )
        elif recipe == "memory-recent":
            res = memory_recent(
                base_url,
                limit=limit,
                kind=kind_filter,
                include_quarantined=include_quarantined,
                include_deleted=include_deleted,
                auth_token=token,
                routes=routes,
            )
        elif recipe == "memory-retrieve":
            q_opt: str | None = str(args.q or "").strip() or None
            res = memory_retrieve(
                base_url,
                q=q_opt,
                limit=limit,
                kind=kind_filter,
                module=module_filter,
                min_trust=args.min_trust,
                max_age_sec=args.max_age_sec,
                include_quarantined=include_quarantined,
                include_deleted=include_deleted,
                auth_token=token,
                routes=routes,
            )
        elif recipe == "memory-stats":
            res = memory_stats(base_url, auth_token=token, routes=routes)
        elif recipe == "memory-feedback":
            if args.id is None or args.rating is None:
                print("id and rating required", file=sys.stderr)
                return 2
            res = memory_feedback(
                base_url,
                int(args.id),
                int(args.rating),
                notes=str(args.notes or "").strip() or None,
                auth_token=token,
                routes=routes,
            )
        elif recipe == "task-add":
            title = str(args.title or "").strip()
            if not title:
                print("title required", file=sys.stderr)
                return 2
            prio = str(args.prio or "p2").strip().lower()
            if prio not in {"p0", "p1", "p2"}:
                prio = "p2"
            owner = str(args.owner or "").strip() or None
            next_step = str(args.next_step or "").strip() or None
            content_lines = [
                "Status: open",
                f"Priority: {prio}",
            ]
            if owner:
                content_lines.append(f"Owner: {owner}")
            if next_step:
                content_lines.append(f"NextStep: {next_step}")
            tags = [str(t) for t in (args.tags or []) if str(t).strip()]
            tags = ["task", "status:open", f"prio:{prio}", *tags]
            res = memory_write(
                base_url,
                summary=f"[TASK] {title}",
                content="\n".join(content_lines),
                kind="task",
                tags=tags,
                source=str(args.source or "") or None,
                author=str(args.author or "") or None,
                module=str(args.module or "") or None,
                auth_token=token,
                routes=routes,
            )
        elif recipe == "task-close":
            if args.id is None:
                print("id required", file=sys.stderr)
                return 2
            task_id = int(args.id)
            tags = [str(t) for t in (args.tags or []) if str(t).strip()]
            tags = ["task", "status:done", f"task_id:{task_id}", *tags]
            content_lines = [
                f"TaskId: {task_id}",
                "Status: done",
            ]
            note = str(args.notes or "").strip() or None
            if note:
                content_lines.append(f"Notes: {note}")
            res = memory_write(
                base_url,
                summary=f"[TASK-CLOSE] {task_id}",
                content="\n".join(content_lines),
                kind="event",
                tags=tags,
                source=str(args.source or "") or None,
                author=str(args.author or "") or None,
                module=str(args.module or "") or None,
                auth_token=token,
                routes=routes,
            )
        ok = 200 <= int(res.status) < 300
        if args.json:
            if isinstance(res.json, dict) and isinstance(res.json.get("results"), list):
                for it in res.json.get("results") or []:
                    if isinstance(it, dict):
                        _print_json({"ok": ok, "record": it})
            else:
                _print_json({"ok": ok, "status": int(res.status), "json": res.json})
        else:
            if isinstance(res.json, dict) and isinstance(res.json.get("results"), list):
                for it in res.json.get("results") or []:
                    if isinstance(it, dict):
                        _print_tab([it.get("id", ""), it.get("kind", ""), it.get("summary", "")])
            else:
                _print_tab(["ok" if ok else "error", int(res.status), "" if res.json is None else "json"])
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
