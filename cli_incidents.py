from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

from utils import _print_json, _print_tab, _read_text, _write_text_atomic


def _date_iso() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def _render_template(template: str, *, title: str, incident_id: str, date: str, severity: str, status: str) -> str:
    out = template
    out = out.replace("<title>", title)
    out = out.replace("<YYYY-MM-DD_short_name>", incident_id)
    out = out.replace("<YYYY-MM-DD>", date)
    out = out.replace("<p0|p1|p2|p3>", severity)
    out = out.replace("<open|mitigated|resolved>", status)
    if not out.endswith("\n"):
        out += "\n"
    return out


def _update_index(index_path: Path, *, date: str, title: str, rel_path: str) -> bool:
    text = _read_text(index_path)
    if not text:
        return False
    if rel_path in text:
        return False

    lines = text.splitlines()
    insert_at = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "## Список":
            insert_at = i + 1
            break

    entry = f"- {date}: [{title}]({rel_path})"
    lines.insert(insert_at, entry)
    new_text = "\n".join(lines).rstrip() + "\n"
    _write_text_atomic(index_path, new_text, backup=True)
    return True


def _cmd_incidents_new(args: argparse.Namespace) -> int:
    cwd = Path(os.getcwd())
    docs_dir = (cwd / "docs").resolve()
    template_path = (docs_dir / "INCIDENT_TEMPLATE.md").resolve()
    index_path = (docs_dir / "INCIDENTS.md").resolve()
    out_dir = (docs_dir / "incidents").resolve()

    incident_id = str(args.id).strip()
    title = str(args.title).strip()
    severity = str(args.severity).strip()
    status = str(args.status).strip()
    date = str(args.date or "").strip() or _date_iso()

    if not incident_id:
        return 2
    if not title:
        return 2

    template = _read_text(template_path) or ""
    if not template:
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = (out_dir / f"{incident_id}.md").resolve()
    rel = f"incidents/{incident_id}.md"

    payload: dict[str, Any] = {
        "kind": "incident_new",
        "id": incident_id,
        "title": title,
        "severity": severity,
        "status": status,
        "date": date,
        "artifacts": {"incident_md": str(out_path), "index_md": str(index_path)},
    }

    if args.dry_run:
        if args.json:
            _print_json(payload)
        else:
            _print_tab(["dry_run", 1])
            _print_tab(["incident", out_path])
        return 0

    rendered = _render_template(template, title=title, incident_id=incident_id, date=date, severity=severity, status=status)
    _write_text_atomic(out_path, rendered, backup=True)

    index_updated = False
    if bool(args.update_index) and index_path.exists():
        try:
            index_updated = _update_index(index_path, date=date, title=title, rel_path=rel)
        except Exception:
            index_updated = False
    payload["index_updated"] = index_updated

    if args.json:
        _print_json(payload)
    else:
        _print_tab(["incident", out_path])
        _print_tab(["index_updated", int(index_updated)])
    return 0


def add_incidents_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    inc = sub.add_parser("incidents")
    inc_sub = inc.add_subparsers(dest="inc_cmd", required=True)

    newp = inc_sub.add_parser("new")
    newp.add_argument("--id", required=True)
    newp.add_argument("--title", required=True)
    newp.add_argument("--severity", default="p2")
    newp.add_argument("--status", default="open")
    newp.add_argument("--date", default=None)
    newp.add_argument("--update-index", action="store_true")
    newp.add_argument("--dry-run", action="store_true")
    newp.add_argument("--json", action="store_true")
    newp.set_defaults(func=_cmd_incidents_new)
