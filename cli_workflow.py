from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_memory_client import HttpResult, memory_write_file
from cli_env import _diagnostics_rows, default_roots
from cli_parallel import WorkerError, _map_git_projects
from cli_select import _abort_if_roots_invalid, _projects_from_args
from git_ops import _git_origin_url, _normalize_github
from scan import _project_kind
from session_close_ops import run_session_close
from utils import _print_json, _print_tab, _write_text_atomic
from zapovednik_policy import DEFAULT_PROFILE, ZapovednikPolicy, get_policy
from zapovednik import append_message, current_session_path, finalize_session, session_health, show, start_session


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


_SENSITIVE_PATH_KEYWORDS = (
    "token",
    "secret",
    "password",
    "passwd",
    "apikey",
    "api-key",
    "auth",
    "credential",
    "private-key",
    "access-key",
    "bearer",
)
_LONG_HEX_RE = re.compile(r"(?i)^[0-9a-f]{20,}$")
_LONG_TOKENISH_RE = re.compile(r"^[A-Za-z0-9_\-]{28,}$")


def _is_sensitive_path_segment(segment: str) -> bool:
    value = str(segment).strip()
    if not value:
        return False
    low = value.lower()
    if any(k in low for k in _SENSITIVE_PATH_KEYWORDS):
        return True
    if _LONG_HEX_RE.fullmatch(value):
        return True
    if _LONG_TOKENISH_RE.fullmatch(value) and any(ch.isdigit() for ch in value):
        return True
    return False


def _safe_session_path_for_output(path: Path) -> tuple[str, bool]:
    p = path.resolve()
    parts = p.parts
    if not parts:
        return str(p), False
    out_parts = [parts[0]]
    redacted = False
    for part in parts[1:]:
        if _is_sensitive_path_segment(part):
            out_parts.append("[REDACTED]")
            redacted = True
        else:
            out_parts.append(part)
    return str(Path(*out_parts)), redacted


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
        remote_value = "" if isinstance(remote, WorkerError) else remote
        github = _normalize_github(remote_value) if remote_value else ""
        rows.append(
            {
                "name": p.name,
                "path": str(p.path),
                "kind": _project_kind(p.path),
                "remote": remote_value,
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


def _capture_cli_call(func: Callable[[argparse.Namespace], int], args: argparse.Namespace) -> tuple[int, str, str]:
    import io

    code = 2
    o = io.StringIO()
    e = io.StringIO()
    try:
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            code = int(func(args))
    except SystemExit as se:
        try:
            code = int(getattr(se, "code", 2) or 2)
        except Exception:
            code = 2
    except Exception as ex:
        code = 1
        print(f"workflow_error: {type(ex).__name__}: {ex}", file=sys.stderr)
    return code, o.getvalue(), e.getvalue()


def _inject_incident_artifacts(incident_path: Path, *, commands: list[str], artifacts: list[tuple[str, Path]]) -> bool:
    try:
        text = incident_path.read_text(encoding="utf-8")
    except OSError:
        return False

    lines = text.splitlines()

    def rel(p: Path) -> str:
        try:
            return os.path.relpath(str(p.resolve()), start=str(incident_path.parent.resolve())).replace("\\", "/")
        except Exception:
            return str(p)

    insert_after = None
    for i, ln in enumerate(lines):
        if ln.strip() == "- Commands:":
            insert_after = i
            break
    if insert_after is not None:
        add_lines = [f"  - `{cmd}`" for cmd in commands]
        lines[insert_after + 1 : insert_after + 1] = add_lines

    insert_after = None
    for i, ln in enumerate(lines):
        if ln.strip() == "- Artifacts (`reports/`):":
            insert_after = i
            break
    if insert_after is not None:
        add_lines = [f"  - [{name}]({rel(path)})" for name, path in artifacts]
        lines[insert_after + 1 : insert_after + 1] = add_lines
    else:
        lines.append("")
        lines.append("## Artifacts")
        for name, path in artifacts:
            lines.append(f"- [{name}]({rel(path)})")

    new_text = "\n".join(lines).rstrip() + "\n"
    _write_text_atomic(incident_path, new_text, backup=True)
    return True


def _cmd_workflow_incident_start(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())

    incident_id = str(args.id).strip()
    title = str(args.title).strip()
    severity = str(args.severity).strip()
    status = str(args.status).strip()
    date = str(args.date or "").strip() or time.strftime("%Y-%m-%d", time.localtime())
    reports_dir = Path(args.reports_dir).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)

    prefix = str(args.prefix or "").strip() or f"incident_start_{incident_id}_{_timestamp()}"
    summary_path = reports_dir / f"{prefix}.summary.json"
    errors_path = reports_dir / f"{prefix}.errors.log"
    perf_path = reports_dir / f"{prefix}.perf.json"
    quality_path = reports_dir / f"{prefix}.quality.json"

    from cli_incidents import _cmd_incidents_new
    from cli_perf import _cmd_perf_baseline
    from cli_quality import _cmd_quality_summary

    errors: list[str] = []
    artifacts: dict[str, str] = {
        "summary_json": str(summary_path),
        "errors_log": str(errors_path),
        "perf_json": str(perf_path),
        "quality_json": str(quality_path),
    }

    incident_args = argparse.Namespace(
        id=incident_id,
        title=title,
        severity=severity,
        status=status,
        date=date,
        update_index=bool(args.update_index),
        dry_run=bool(args.dry_run),
        json=True,
    )
    inc_code, inc_out, inc_err = _capture_cli_call(_cmd_incidents_new, incident_args)
    if inc_err.strip():
        errors.append(inc_err.strip())

    incident_md = (cwd / "docs" / "incidents" / f"{incident_id}.md").resolve()
    index_md = (cwd / "docs" / "INCIDENTS.md").resolve()
    artifacts["incident_md"] = str(incident_md)
    artifacts["index_md"] = str(index_md)

    quality_args = argparse.Namespace(
        json=True,
        no_run=bool(args.quality_no_run),
        fail_under=int(args.quality_fail_under),
        write_report=str(quality_path),
    )
    q_code, q_out, q_err = _capture_cli_call(_cmd_quality_summary, quality_args)
    if q_err.strip():
        errors.append(q_err.strip())

    perf_args = argparse.Namespace(
        roots=list(args.roots or []),
        max_depth=int(args.max_depth),
        jobs=int(args.jobs),
        report_max_depth=int(args.report_max_depth),
        repeat=int(args.repeat),
        compare_to=None,
        max_degradation_pct=20.0,
        write_report=str(perf_path),
        json=True,
    )
    p_code, p_out, p_err = _capture_cli_call(_cmd_perf_baseline, perf_args)
    if p_err.strip():
        errors.append(p_err.strip())

    commands = [
        f"python -m integrator quality summary --fail-under {int(args.quality_fail_under)}"
        + (" --no-run" if bool(args.quality_no_run) else "")
        + f" --write-report {quality_path}",
        f"python -m integrator perf baseline --repeat {int(args.repeat)} --write-report {perf_path}",
    ]

    artifact_links = [
        ("workflow summary", summary_path),
        ("quality summary", quality_path),
        ("perf baseline", perf_path),
        ("errors log", errors_path),
    ]

    injected = False
    if not bool(args.dry_run) and incident_md.exists():
        injected = _inject_incident_artifacts(incident_md, commands=commands, artifacts=artifact_links)

    payload: dict[str, Any] = {
        "kind": "workflow_incident_start",
        "cwd": str(cwd),
        "incident": {
            "id": incident_id,
            "title": title,
            "severity": severity,
            "status": status,
            "date": date,
            "dry_run": bool(args.dry_run),
            "code": int(inc_code),
        },
        "quality": {"code": int(q_code), "report": str(quality_path), "no_run": bool(args.quality_no_run)},
        "perf": {"code": int(p_code), "report": str(perf_path), "repeat": int(args.repeat)},
        "incident_updated": bool(injected),
        "artifacts": artifacts,
    }

    _write_json(summary_path, payload)
    _write_text(errors_path, "\n".join([e for e in errors if e.strip()]))

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["incident", incident_id, title])
        _print_tab(["incident_md", str(incident_md)])
        _print_tab(["quality_json", str(quality_path)])
        _print_tab(["perf_json", str(perf_path)])
        _print_tab(["summary_json", str(summary_path)])
        _print_tab(["errors_log", str(errors_path)])

    any_failed = any(int(c) != 0 for c in [inc_code, q_code, p_code])
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

    inc = wf_sub.add_parser("incident")
    inc_sub = inc.add_subparsers(dest="incident_cmd", required=True)

    start = inc_sub.add_parser("start")
    start.add_argument("--id", required=True)
    start.add_argument("--title", required=True)
    start.add_argument("--severity", default="p2")
    start.add_argument("--status", default="open")
    start.add_argument("--date", default=None)
    start.add_argument("--update-index", action="store_true")

    start.add_argument("--roots", nargs="*", default=None)
    start.add_argument("--max-depth", type=int, default=3)
    start.add_argument("--jobs", type=int, default=16)
    start.add_argument("--report-max-depth", type=int, default=2)
    start.add_argument("--repeat", type=int, default=1)

    start.add_argument("--quality-no-run", action="store_true")
    start.add_argument("--quality-fail-under", type=int, default=80)

    start.add_argument("--reports-dir", default="reports")
    start.add_argument("--prefix", default=None)
    start.add_argument("--dry-run", action="store_true")
    start.add_argument("--json", action="store_true")
    start.set_defaults(func=_cmd_workflow_incident_start)

    zap = wf_sub.add_parser("zapovednik")
    zap_sub = zap.add_subparsers(dest="zap_cmd", required=True)

    z_start = zap_sub.add_parser("start")
    z_start.add_argument("--json", action="store_true")
    z_start.set_defaults(func=_cmd_zapovednik_start)

    z_append = zap_sub.add_parser("append")
    z_append.add_argument("--role", default="user")
    z_append.add_argument("--path", default=None)
    z_append.add_argument("--text", default=None)
    z_append.add_argument("--text-file", default=None)
    z_append.add_argument("--meta-json", default=None)
    z_append.add_argument("--auto-finalize-on-threshold", action="store_true")
    z_append.add_argument("--profile", choices=["research", "coding", "ops"], default=DEFAULT_PROFILE)
    z_append.add_argument("--context-window-tokens", type=int, default=None)
    z_append.add_argument("--message-soft-limit", type=int, default=None)
    z_append.add_argument("--size-soft-limit-kb", type=int, default=None)
    z_append.add_argument("--token-soft-ratio", type=float, default=None)
    z_append.add_argument("--token-hard-ratio", type=float, default=None)
    z_append.add_argument("--min-repeated-tokens", type=int, default=None)
    z_append.add_argument("--min-repeat-frequency", type=int, default=None)
    z_append.add_argument("--score-threshold", type=float, default=None)
    z_append.add_argument("--latency-degradation", type=float, default=None)
    z_append.add_argument("--json", action="store_true")
    z_append.set_defaults(func=_cmd_zapovednik_append)

    z_fin = zap_sub.add_parser("finalize")
    z_fin.add_argument("--path", default=None)
    z_fin.add_argument("--json", action="store_true")
    z_fin.set_defaults(func=_cmd_zapovednik_finalize)

    z_show = zap_sub.add_parser("show")
    z_show.add_argument("--path", default=None)
    z_show.set_defaults(func=_cmd_zapovednik_show)

    z_health = zap_sub.add_parser("health")
    z_health.add_argument("--path", default=None)
    z_health.add_argument("--profile", choices=["research", "coding", "ops"], default=DEFAULT_PROFILE)
    z_health.add_argument("--context-window-tokens", type=int, default=None)
    z_health.add_argument("--message-soft-limit", type=int, default=None)
    z_health.add_argument("--size-soft-limit-kb", type=int, default=None)
    z_health.add_argument("--token-soft-ratio", type=float, default=None)
    z_health.add_argument("--token-hard-ratio", type=float, default=None)
    z_health.add_argument("--min-repeated-tokens", type=int, default=None)
    z_health.add_argument("--min-repeat-frequency", type=int, default=None)
    z_health.add_argument("--score-threshold", type=float, default=None)
    z_health.add_argument("--latency-degradation", type=float, default=None)
    z_health.add_argument("--json", action="store_true")
    z_health.set_defaults(func=_cmd_zapovednik_health)

    session = wf_sub.add_parser("session")
    session_sub = session.add_subparsers(dest="session_cmd", required=True)

    close = session_sub.add_parser("close")
    close.add_argument("--reports-dir", default="reports")
    close.add_argument("--date", default=None)
    close.add_argument("--owner", default="AI Agent (Integrator CLI Engineer)")
    close.add_argument("--task-id", default="B16")
    close.add_argument("--dry-run", action="store_true")
    close.add_argument("--skip-quality", action="store_true")
    close.add_argument("--json", action="store_true")
    close.set_defaults(func=_cmd_workflow_session_close)


def _cmd_zapovednik_start(args: argparse.Namespace) -> int:
    path = start_session().resolve()
    safe_path, masked = _safe_session_path_for_output(path)
    if args.json:
        _print_json({"kind": "zapovednik_start", "path": safe_path, "path_masked": bool(masked), "success": True})
    else:
        _print_tab(["zapovednik", safe_path])
        _print_tab(["path_masked", "1" if masked else "0"])
        _print_tab(["success", "1"])
    return 0


def _load_text_arg(text: str | None, text_file: str | None) -> str:
    if text is not None and str(text).strip():
        return str(text)
    if text_file:
        p = Path(text_file)
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


def _load_meta_json(meta_json: str | None) -> dict[str, object] | None:
    if not meta_json or not str(meta_json).strip():
        return None
    try:
        obj = json.loads(meta_json)
    except json.JSONDecodeError:
        return {"meta_json_error": "invalid_json"}
    if isinstance(obj, dict):
        return {str(k): v for k, v in obj.items()}
    return {"meta_json_error": "not_object"}


def _resolve_health_thresholds(args: argparse.Namespace) -> ZapovednikPolicy:
    policy = get_policy(str(getattr(args, "profile", DEFAULT_PROFILE)))
    if getattr(args, "context_window_tokens", None) is not None:
        policy["context_window_tokens"] = int(args.context_window_tokens)
    if getattr(args, "message_soft_limit", None) is not None:
        policy["message_soft_limit"] = int(args.message_soft_limit)
    if getattr(args, "size_soft_limit_kb", None) is not None:
        policy["size_soft_limit_kb"] = int(args.size_soft_limit_kb)
    if getattr(args, "token_soft_ratio", None) is not None:
        policy["token_soft_ratio"] = float(args.token_soft_ratio)
    if getattr(args, "token_hard_ratio", None) is not None:
        policy["token_hard_ratio"] = float(args.token_hard_ratio)
    if getattr(args, "min_repeated_tokens", None) is not None:
        policy["min_repeated_tokens"] = int(args.min_repeated_tokens)
    if getattr(args, "min_repeat_frequency", None) is not None:
        policy["min_repeat_frequency"] = int(args.min_repeat_frequency)
    if getattr(args, "score_threshold", None) is not None:
        policy["score_threshold"] = float(args.score_threshold)
    if getattr(args, "latency_degradation", None) is not None:
        policy["latency_degradation"] = float(args.latency_degradation)
    return policy


def _cmd_zapovednik_append(args: argparse.Namespace) -> int:
    text = _load_text_arg(args.text, args.text_file)
    meta = _load_meta_json(args.meta_json)
    p = Path(args.path).resolve() if args.path else None
    auto_finalize_triggered = False
    auto_finalize_reasons: list[str] = []
    recommend_close_before_append = False
    thresholds = _resolve_health_thresholds(args)
    if bool(args.auto_finalize_on_threshold) and p is None:
        health = session_health(
            context_window_tokens=int(thresholds["context_window_tokens"]),
            message_soft_limit=int(thresholds["message_soft_limit"]),
            size_soft_limit_kb=int(thresholds["size_soft_limit_kb"]),
            token_soft_ratio=float(thresholds["token_soft_ratio"]),
            token_hard_ratio=float(thresholds["token_hard_ratio"]),
            min_repeated_tokens=int(thresholds["min_repeated_tokens"]),
            min_repeat_frequency=int(thresholds["min_repeat_frequency"]),
            score_threshold=float(thresholds["score_threshold"]),
            latency_degradation=float(thresholds["latency_degradation"]),
        )
        recommend_close_before_append = bool(health.get("recommend_close"))
        raw_reasons = health.get("recommend_close_reasons", [])
        if isinstance(raw_reasons, list):
            auto_finalize_reasons = [str(x) for x in raw_reasons if isinstance(x, str)]
        if recommend_close_before_append and not bool(health.get("session_closed")):
            finalize_session()
            auto_finalize_triggered = True
    path = append_message(str(args.role), text, meta=meta, path=p)
    if args.json:
        _print_json(
            {
                "kind": "zapovednik_append",
                "path": str(path),
                "auto_finalize_triggered": bool(auto_finalize_triggered),
                "recommend_close_before_append": bool(recommend_close_before_append),
                "auto_finalize_reasons": auto_finalize_reasons,
                "profile": str(args.profile),
            }
        )
    else:
        _print_tab(["zapovednik", str(path)])
        _print_tab(["auto_finalize_triggered", "1" if auto_finalize_triggered else "0"])
    return 0


def _cmd_zapovednik_finalize(args: argparse.Namespace) -> int:
    p = Path(args.path).resolve() if args.path else None
    path = finalize_session(path=p)
    if args.json:
        _print_json({"kind": "zapovednik_finalize", "path": str(path)})
    else:
        _print_tab(["zapovednik", str(path)])
    return 0


def _cmd_zapovednik_show(args: argparse.Namespace) -> int:
    p = Path(args.path).resolve() if args.path else current_session_path()
    print(show(p), end="")
    return 0


def _cmd_zapovednik_health(args: argparse.Namespace) -> int:
    p = Path(args.path).resolve() if args.path else None
    thresholds = _resolve_health_thresholds(args)
    payload = session_health(
        path=p,
        context_window_tokens=int(thresholds["context_window_tokens"]),
        message_soft_limit=int(thresholds["message_soft_limit"]),
        size_soft_limit_kb=int(thresholds["size_soft_limit_kb"]),
        token_soft_ratio=float(thresholds["token_soft_ratio"]),
        token_hard_ratio=float(thresholds["token_hard_ratio"]),
        min_repeated_tokens=int(thresholds["min_repeated_tokens"]),
        min_repeat_frequency=int(thresholds["min_repeat_frequency"]),
        score_threshold=float(thresholds["score_threshold"]),
        latency_degradation=float(thresholds["latency_degradation"]),
    )
    out = {"kind": "zapovednik_health", "profile": str(args.profile), **payload}
    if args.json:
        _print_json(out)
    else:
        _print_tab(["path", str(out.get("path", ""))])
        _print_tab(["messages_total", str(out.get("messages_total", 0))])
        _print_tab(["approx_tokens", str(out.get("approx_tokens", 0))])
        _print_tab(["token_ratio", str(out.get("token_ratio", 0.0))])
        _print_tab(["close_score", str(out.get("close_score", 0.0))])
        _print_tab(["recommend_close", "1" if bool(out.get("recommend_close")) else "0"])
    return 0


def _cmd_workflow_session_close(args: argparse.Namespace) -> int:
    payload = run_session_close(
        root=Path.cwd(),
        reports_dir=str(args.reports_dir),
        date=str(args.date).strip() if args.date else None,
        owner=str(args.owner),
        task_id=str(args.task_id),
        dry_run=bool(args.dry_run),
        skip_quality=bool(args.skip_quality),
    )
    if args.json:
        _print_json(payload)
    else:
        _print_tab(["kind", str(payload.get("kind", ""))])
        _print_tab(["status", str(payload.get("status", ""))])
        _print_tab(["task_id", str(payload.get("task_id", ""))])
        artifacts = payload.get("artifacts", {})
        if isinstance(artifacts, dict):
            _print_tab(["session_close_json", str(artifacts.get("session_close_json", ""))])
            _print_tab(["execution_report", str(artifacts.get("execution_report", ""))])
    return int(payload.get("exit_code", 1))
