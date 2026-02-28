from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cli_env import default_vault_root
from utils import _print_json, _print_tab, _run_capture


_ATTACH_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
}


def add_obsidian_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    obs = sub.add_parser("obsidian")
    obs_sub = obs.add_subparsers(dest="obsidian_cmd", required=True)

    doctor = obs_sub.add_parser("doctor")
    doctor.add_argument("--obsidian-bin", default="obsidian")
    doctor.add_argument("--vault-root", default=str(default_vault_root()))
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=_cmd_obsidian_doctor)

    search = obs_sub.add_parser("search")
    search.add_argument("--obsidian-bin", default="obsidian")
    search.add_argument("--vault", default=None)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=_cmd_obsidian_search)

    tags = obs_sub.add_parser("tags")
    tags_sub = tags.add_subparsers(dest="obsidian_tags_cmd", required=True)
    counts = tags_sub.add_parser("counts")
    counts.add_argument("--obsidian-bin", default="obsidian")
    counts.add_argument("--vault", default=None)
    counts.add_argument("--json", action="store_true")
    counts.set_defaults(func=_cmd_obsidian_tags_counts)

    attachments = obs_sub.add_parser("attachments")
    att_sub = attachments.add_subparsers(dest="obsidian_attachments_cmd", required=True)

    report = att_sub.add_parser("report")
    report.add_argument("--vault-root", default=str(default_vault_root()))
    report.add_argument("--reports-dir", default="reports")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=_cmd_obsidian_attachments_report)

    delete = att_sub.add_parser("delete")
    delete.add_argument("--vault-root", default=str(default_vault_root()))
    delete.add_argument("--report-json", required=True)
    delete.add_argument("--backup-dir", required=True)
    delete.add_argument("--apply", action="store_true")
    delete.add_argument("--json", action="store_true")
    delete.set_defaults(func=_cmd_obsidian_attachments_delete)

    ev = obs_sub.add_parser("eval")
    ev.add_argument("--obsidian-bin", default="obsidian")
    ev.add_argument("--vault", default=None)
    ev.add_argument("--enable-eval", action="store_true")
    ev.add_argument("--profile", required=True, choices=sorted(_eval_profiles().keys()))
    ev.add_argument("--json", action="store_true")
    ev.set_defaults(func=_cmd_obsidian_eval)


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _vault_markers(vault_root: Path) -> list[str]:
    markers: list[str] = []
    if (vault_root / ".obsidian").exists():
        markers.append(".obsidian")
    if (vault_root / "KB").exists():
        markers.append("KB")
    if (vault_root / "Notes").exists():
        markers.append("Notes")
    return markers


def _obsidian_kv(key: str, value: str) -> str:
    return f"{key}={value}"


def _run_obsidian(obsidian_bin: str, args: list[str]) -> tuple[int, str, str]:
    return _run_capture([obsidian_bin, *args], cwd=Path(".").resolve())


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def _cmd_obsidian_doctor(args: argparse.Namespace) -> int:
    obsidian_bin = str(args.obsidian_bin or "").strip() or "obsidian"
    vault_root = Path(str(args.vault_root)).resolve()

    code, out, err = _run_obsidian(obsidian_bin, ["version"])
    version = (out or "").strip()
    present = code == 0 and bool(version)
    status = "ok" if present else ("missing" if code == 127 else "error")

    payload: dict[str, Any] = {
        "obsidian_cli_present": bool(present),
        "obsidian_version": version or None,
        "vault_root": str(vault_root),
        "vault_markers": _vault_markers(vault_root),
        "status": status,
    }

    if args.json:
        _print_json(payload)
    else:
        _print_tab([payload["status"], int(payload["obsidian_cli_present"]), payload["obsidian_version"] or "", payload["vault_root"]])
        for m in payload["vault_markers"]:
            _print_tab(["marker", m])
        if err.strip():
            _print_tab(["stderr", err.strip()])
    return 0 if status == "ok" else 1


def _normalize_search_results(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        out: list[dict[str, Any]] = []
        for it in parsed["results"]:
            if isinstance(it, dict):
                out.append(dict(it))
        return out
    if isinstance(parsed, list):
        out2: list[dict[str, Any]] = []
        for it in parsed:
            if isinstance(it, dict):
                out2.append(dict(it))
        return out2
    return []


def _cmd_obsidian_search(args: argparse.Namespace) -> int:
    obsidian_bin = str(args.obsidian_bin or "").strip() or "obsidian"
    vault = str(args.vault or "").strip() or None
    query = str(args.query or "").strip()
    limit = max(1, int(args.limit))
    if not query:
        print("query required", file=sys.stderr)
        return 2

    cmd: list[str] = ["search", _obsidian_kv("query", query), _obsidian_kv("limit", str(limit)), _obsidian_kv("format", "json")]
    if vault:
        cmd.append(_obsidian_kv("vault", vault))
    code, out, err = _run_obsidian(obsidian_bin, cmd)
    parsed = _safe_json_loads(out)
    items = _normalize_search_results(parsed)
    ok = code == 0
    if args.json:
        for it in items:
            _print_json({"kind": "obsidian_search_result", "vault": vault, "payload": it})
        _print_json({"kind": "obsidian_search_summary", "vault": vault, "ok": ok, "count": len(items)})
    else:
        for it in items:
            path = it.get("path") or it.get("file") or ""
            line = it.get("line") or it.get("ln") or ""
            match = it.get("match") or it.get("text") or ""
            _print_tab([path, line, match])
        if err.strip():
            _print_tab(["stderr", err.strip()])
    return 0 if ok else 1


def _normalize_tag_counts(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
        out: list[dict[str, Any]] = []
        for it in parsed["results"]:
            if isinstance(it, dict):
                out.append(dict(it))
        return out
    if isinstance(parsed, list):
        out2: list[dict[str, Any]] = []
        for it in parsed:
            if isinstance(it, dict):
                out2.append(dict(it))
        return out2
    return []


def _cmd_obsidian_tags_counts(args: argparse.Namespace) -> int:
    obsidian_bin = str(args.obsidian_bin or "").strip() or "obsidian"
    vault = str(args.vault or "").strip() or None
    cmd: list[str] = ["tags", "all", "counts", _obsidian_kv("format", "json")]
    if vault:
        cmd.append(_obsidian_kv("vault", vault))
    code, out, err = _run_obsidian(obsidian_bin, cmd)
    parsed = _safe_json_loads(out)
    items = _normalize_tag_counts(parsed)
    ok = code == 0
    if args.json:
        for it in items:
            _print_json({"kind": "obsidian_tag_count", "vault": vault, "payload": it})
        _print_json({"kind": "obsidian_tags_summary", "vault": vault, "ok": ok, "count": len(items)})
    else:
        for it in items:
            tag = it.get("tag") or it.get("name") or ""
            count = it.get("count") or it.get("n") or ""
            _print_tab([tag, count])
        if err.strip():
            _print_tab(["stderr", err.strip()])
    return 0 if ok else 1


_WIKI_LINK_RE = re.compile(r"!?\[\[([^\]]+)\]\]")
_MD_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")


def _normalize_wikilink_target(raw: str) -> str:
    s = (raw or "").strip()
    if "|" in s:
        s = s.split("|", 1)[0].strip()
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    if "^" in s:
        s = s.split("^", 1)[0].strip()
    return s.strip()


def _normalize_md_target(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("<") and s.endswith(">"):
        s = s[1:-1].strip()
    if s.startswith("file:") or "://" in s:
        return ""
    s = s.split("#", 1)[0].strip()
    s = s.split("?", 1)[0].strip()
    return s.strip()


def _referenced_targets(vault_root: Path) -> set[str]:
    refs: set[str] = set()
    for p in vault_root.rglob("*.md"):
        if ".obsidian" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _WIKI_LINK_RE.finditer(text):
            t = _normalize_wikilink_target(m.group(1))
            if t:
                refs.add(t.lower())
                refs.add(Path(t).name.lower())
        for m in _MD_LINK_RE.finditer(text):
            t = _normalize_md_target(m.group(1))
            if not t:
                continue
            refs.add(t.replace("\\", "/").lower())
            refs.add(Path(t).name.lower())
    return refs


@dataclass(frozen=True)
class AttachmentCandidate:
    path: str
    rel: str
    size: int


def _attachments_report(vault_root: Path) -> list[AttachmentCandidate]:
    refs = _referenced_targets(vault_root)
    items: list[AttachmentCandidate] = []
    for p in vault_root.rglob("*"):
        if not p.is_file():
            continue
        if ".obsidian" in p.parts:
            continue
        if p.suffix.lower() not in _ATTACH_EXTS:
            continue
        try:
            rel = p.relative_to(vault_root).as_posix()
        except Exception:
            continue
        key1 = rel.lower()
        key2 = p.name.lower()
        if key1 in refs or key2 in refs:
            continue
        try:
            size = int(p.stat().st_size)
        except OSError:
            size = 0
        items.append(AttachmentCandidate(path=str(p), rel=rel, size=size))
    items.sort(key=lambda x: x.rel)
    return items


def _cmd_obsidian_attachments_report(args: argparse.Namespace) -> int:
    vault_root = Path(str(args.vault_root)).resolve()
    reports_dir = Path(str(args.reports_dir)).resolve()
    reports_dir.mkdir(parents=True, exist_ok=True)
    candidates = _attachments_report(vault_root)
    report_path = reports_dir / f"obsidian_attachments_report_{_timestamp()}.json"
    payload = {
        "vault_root": str(vault_root),
        "count": len(candidates),
        "candidates": [{"rel": c.rel, "path": c.path, "size": c.size} for c in candidates],
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        _print_json({"kind": "obsidian_attachments_report", "report_json": str(report_path), "count": len(candidates), "vault_root": str(vault_root)})
        for c in candidates:
            _print_json({"kind": "obsidian_attachment_candidate", "payload": {"rel": c.rel, "path": c.path, "size": c.size}})
    else:
        _print_tab(["report_json", str(report_path)])
        _print_tab(["count", str(len(candidates))])
        for c in candidates:
            _print_tab(["orphan", c.rel, c.size])
    return 0


def _cmd_obsidian_attachments_delete(args: argparse.Namespace) -> int:
    if not bool(args.apply):
        print("apply required", file=sys.stderr)
        return 2
    vault_root = Path(str(args.vault_root)).resolve()
    report_json = Path(str(args.report_json)).resolve()
    backup_dir = Path(str(args.backup_dir)).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        raw = json.loads(report_json.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"bad report_json: {exc}", file=sys.stderr)
        return 2
    candidates_raw = raw.get("candidates") if isinstance(raw, dict) else None
    if not isinstance(candidates_raw, list):
        print("bad report_json: candidates missing", file=sys.stderr)
        return 2

    deleted = 0
    failed = 0
    for it in candidates_raw:
        if not isinstance(it, dict):
            continue
        rel = str(it.get("rel") or "")
        if not rel:
            continue
        src = (vault_root / Path(rel)).resolve()
        try:
            src.relative_to(vault_root)
        except Exception:
            failed += 1
            if args.json:
                _print_json({"kind": "obsidian_attachment_delete", "ok": False, "rel": rel, "error": "outside_vault"})
            continue
        dst = (backup_dir / Path(rel)).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if src.exists():
                shutil.copy2(src, dst)
                src.unlink()
                deleted += 1
                if args.json:
                    _print_json({"kind": "obsidian_attachment_delete", "ok": True, "rel": rel, "backup_path": str(dst)})
            else:
                if args.json:
                    _print_json({"kind": "obsidian_attachment_delete", "ok": True, "rel": rel, "status": "missing"})
        except Exception as exc:
            failed += 1
            if args.json:
                _print_json({"kind": "obsidian_attachment_delete", "ok": False, "rel": rel, "error": str(exc)})

    summary = {"kind": "obsidian_attachments_delete_summary", "deleted": deleted, "failed": failed, "backup_dir": str(backup_dir)}
    if args.json:
        _print_json(summary)
    else:
        _print_tab(["deleted", str(deleted)])
        _print_tab(["failed", str(failed)])
        _print_tab(["backup_dir", str(backup_dir)])
    return 0 if failed == 0 else 1


def _eval_profiles() -> dict[str, str]:
    return {
        "files_count": "(() => { try { return String(app.vault.getFiles().length); } catch (e) { return ''; } })()",
        "active_file_path": "(() => { try { const f=app.workspace.getActiveFile(); return f ? String(f.path) : ''; } catch (e) { return ''; } })()",
        "vault_name": "(() => { try { return String(app.vault.getName ? app.vault.getName() : ''); } catch (e) { return ''; } })()",
    }


def _cmd_obsidian_eval(args: argparse.Namespace) -> int:
    if not bool(args.enable_eval):
        payload = {"kind": "obsidian_eval", "status": "disabled", "profile": str(args.profile)}
        if args.json:
            _print_json(payload)
        else:
            _print_tab(["disabled", str(args.profile)])
        return 1

    obsidian_bin = str(args.obsidian_bin or "").strip() or "obsidian"
    vault = str(args.vault or "").strip() or None
    profile = str(args.profile)
    profiles = _eval_profiles()
    code_str = profiles.get(profile)
    if not code_str:
        print("profile not found", file=sys.stderr)
        return 2

    cmd: list[str] = ["eval", _obsidian_kv("code", code_str)]
    if vault:
        cmd.append(_obsidian_kv("vault", vault))
    code, out, err = _run_obsidian(obsidian_bin, cmd)
    ok = code == 0
    result = (out or "").strip()
    if args.json:
        _print_json({"kind": "obsidian_eval_result", "ok": ok, "profile": profile, "result_len": len(result), "result": result or None})
    else:
        _print_tab(["ok" if ok else "error", profile, len(result)])
        if result:
            _print_tab(["result", result])
        if err.strip():
            _print_tab(["stderr", err.strip()])
    return 0 if ok else 1
