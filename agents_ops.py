from __future__ import annotations

import socket
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

from git_ops import _git_status, _git_status_fields
from scan import Project, _project_kind
from utils import _coerce_int, _path_exists_from_value, _read_json_object, _safe_file_count


def _agent_project_type(project_dir: Path) -> str:
    if (project_dir / "config" / "gateway.json").exists():
        return "gateway"
    if (project_dir / "config" / "media_paths.json").exists():
        return "media-storage"
    if (project_dir / ".trae" / "rules" / "project_rules.md").exists():
        return "trae-project"
    from scan import _is_agent_project_dir

    if _is_agent_project_dir(project_dir):
        return "agent-workflow"
    return ""


def _is_endpoint_up(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _agent_row_problems(row: Mapping[str, object]) -> list[str]:
    problems: list[str] = []

    state = str(row.get("state", "")).strip().lower()
    if state in {"error", "tool-missing"}:
        problems.append(f"git_{state}")

    agent_type = str(row.get("agent_type", "")).strip().lower()
    gateway_base = str(row.get("gateway_base", "")).strip()
    gateway_routes = _coerce_int(row.get("gateway_routes", 0), default=0)
    gateway_up = bool(row.get("gateway_up", False))
    if agent_type == "gateway" or gateway_base:
        if not gateway_base:
            problems.append("gateway_base_missing")
        else:
            if not gateway_up:
                problems.append("gateway_unreachable")
            if gateway_routes <= 0:
                problems.append("gateway_routes_missing")

    if agent_type == "media-storage":
        media_root = str(row.get("media_root", "")).strip()
        work_root = str(row.get("work_root", "")).strip()
        publish_root = str(row.get("publish_root", "")).strip()
        if not media_root:
            problems.append("media_root_empty")
        elif not bool(row.get("media_root_exists", False)):
            problems.append("media_root_missing")
        if not work_root:
            problems.append("work_root_empty")
        elif not bool(row.get("work_root_exists", False)):
            problems.append("work_root_missing")
        if not publish_root:
            problems.append("publish_root_empty")
        elif not bool(row.get("publish_root_exists", False)):
            problems.append("publish_root_missing")

    return problems


def _problem_tags(row: Mapping[str, object]) -> list[str]:
    value = row.get("problems", [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _agent_fix_hints(row: Mapping[str, object]) -> list[str]:
    problems = _agent_row_problems(row)
    if not problems:
        return []
    hints: list[str] = []
    path = Path(str(row.get("path", ""))).resolve()
    gateway_json = path / "config" / "gateway.json"
    media_json = path / "config" / "media_paths.json"

    gateway_base = str(row.get("gateway_base", "")).strip()
    media_root = str(row.get("media_root", "")).strip()
    work_root = str(row.get("work_root", "")).strip()
    publish_root = str(row.get("publish_root", "")).strip()

    for problem in problems:
        if problem == "git_tool-missing":
            hints.append("git --version")
        elif problem == "git_error":
            if path:
                hints.append(f"git -C {path} status")
        elif problem == "gateway_base_missing":
            hints.append(f"Get-Content {gateway_json}")
        elif problem == "gateway_unreachable":
            if gateway_base:
                parsed = urlparse(gateway_base)
                host = parsed.hostname or ""
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                if host:
                    hints.append(f"Test-NetConnection {host} -Port {port}")
        elif problem == "gateway_routes_missing":
            hints.append(f"Get-Content {gateway_json}")
        elif problem in {"media_root_empty", "work_root_empty", "publish_root_empty"}:
            hints.append(f"Get-Content {media_json}")
        elif problem == "media_root_missing" and media_root:
            hints.append(f"Test-Path {media_root}")
        elif problem == "work_root_missing" and work_root:
            hints.append(f"New-Item -ItemType Directory -Force -Path {work_root}")
        elif problem == "publish_root_missing" and publish_root:
            hints.append(f"New-Item -ItemType Directory -Force -Path {publish_root}")

    seen: set[str] = set()
    ordered: list[str] = []
    for hint in hints:
        if hint in seen:
            continue
        seen.add(hint)
        ordered.append(hint)
    return ordered


def _build_agent_row(project: Project) -> dict[str, object]:
    project_type = _agent_project_type(project.path)
    has_git = (project.path / ".git").exists()
    state = ""
    branch = ""
    if has_git:
        gs = _git_status(project.path)
        if gs is not None:
            fields = _git_status_fields(gs)
            state = fields["state"]
            branch = fields["branch"]

    scripts_count = _safe_file_count(project.path / "scripts", "*")
    config_json_count = _safe_file_count(project.path / "config", "*.json")

    gateway_cfg = _read_json_object(project.path / "config" / "gateway.json") or {}
    gateway_base = gateway_cfg.get("base_url", "")
    if not isinstance(gateway_base, str):
        gateway_base = ""
    routes = gateway_cfg.get("routes")
    gateway_routes = len(routes) if isinstance(routes, dict) else 0
    gateway_up = _is_endpoint_up(gateway_base) if gateway_base else False

    media_cfg = _read_json_object(project.path / "config" / "media_paths.json") or {}
    media_root = media_cfg.get("media_root", "")
    work_root = media_cfg.get("work_root", "")
    publish_root = media_cfg.get("publish_root", "")

    row = {
        "name": project.name,
        "path": str(project.path),
        "agent_type": project_type,
        "kind": _project_kind(project.path),
        "git": has_git,
        "state": state,
        "branch": branch,
        "scripts": scripts_count,
        "config_json": config_json_count,
        "gateway_base": gateway_base,
        "gateway_routes": gateway_routes,
        "gateway_up": gateway_up,
        "media_root": media_root,
        "media_root_exists": _path_exists_from_value(media_root),
        "work_root": work_root,
        "work_root_exists": _path_exists_from_value(work_root),
        "publish_root": publish_root,
        "publish_root_exists": _path_exists_from_value(publish_root),
    }
    row["problems"] = _agent_row_problems(row)
    return row
