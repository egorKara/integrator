from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_api import github_api_request, load_github_token
from github_issues import parse_repo_slug


@dataclass(frozen=True)
class WorkerConfig:
    repo_owner: str
    repo_name: str
    labels: list[str]
    state_file: Path
    queue_file: Path
    dry_run: bool
    max_state_items: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        row = json.loads(raw)
    except Exception:
        return None
    return row if isinstance(row, dict) else None


def _save_json(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _build_config(args: argparse.Namespace) -> WorkerConfig:
    raw_repo = (args.repo or os.environ.get("TELEGRAM_BRIDGE_REPO") or "").strip()
    slug = parse_repo_slug(raw_repo)
    if slug is None:
        raise RuntimeError("invalid_repo_slug")
    owner, repo = slug
    labels_raw = (args.labels or "remote,telegram").strip()
    labels = [x.strip() for x in labels_raw.replace(";", ",").split(",") if x.strip()]
    if not labels:
        raise RuntimeError("missing_labels")
    max_state_items = int(args.max_state_items)
    if max_state_items < 100:
        max_state_items = 100
    return WorkerConfig(
        repo_owner=owner,
        repo_name=repo,
        labels=labels,
        state_file=Path(args.state_file).resolve(),
        queue_file=Path(args.queue_file).resolve(),
        dry_run=bool(args.dry_run),
        max_state_items=max_state_items,
    )


def _list_open_issues(config: WorkerConfig, token: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 1
    labels_csv = ",".join(config.labels)
    while True:
        query = urllib.parse.urlencode(
            {
                "state": "open",
                "per_page": 100,
                "page": page,
                "labels": labels_csv,
                "sort": "created",
                "direction": "asc",
            }
        )
        url = f"https://api.github.com/repos/{config.repo_owner}/{config.repo_name}/issues?{query}"
        res = github_api_request("GET", url, token=token, payload=None)
        if not res.ok or not isinstance(res.json, list):
            raise RuntimeError(f"github_list_failed:{res.status}:{res.error_kind or 'unknown'}")
        rows = [x for x in res.json if isinstance(x, dict)]
        if not rows:
            break
        out.extend(rows)
        if len(rows) < 100:
            break
        page += 1
    filtered: list[dict[str, Any]] = []
    for row in out:
        if "pull_request" in row:
            continue
        filtered.append(row)
    return filtered


def _load_state(path: Path) -> set[int]:
    row = _load_json(path)
    if row is None:
        return set()
    raw = row.get("processed_issue_numbers")
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for item in raw:
        if isinstance(item, int):
            out.add(item)
    return out


def _save_state(path: Path, processed: set[int], max_items: int) -> None:
    trimmed = sorted(processed)[-max_items:]
    _save_json(
        path,
        {
            "kind": "telegram_github_worker_state",
            "updated_at_utc": _utc_now(),
            "processed_issue_numbers": trimmed,
        },
    )


def _normalize_labels(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def _ensure_issue_claimed(config: WorkerConfig, token: str | None, issue_number: int, current_labels: list[str]) -> None:
    wanted = list(dict.fromkeys(current_labels + ["agent:queued"]))
    patch_url = f"https://api.github.com/repos/{config.repo_owner}/{config.repo_name}/issues/{issue_number}"
    patch_res = github_api_request("PATCH", patch_url, token=token, payload={"labels": wanted})
    if not patch_res.ok:
        raise RuntimeError(f"github_label_failed:{issue_number}:{patch_res.status}:{patch_res.error_kind or 'unknown'}")
    comment_url = f"https://api.github.com/repos/{config.repo_owner}/{config.repo_name}/issues/{issue_number}/comments"
    comment = (
        "Авто-воркер integrator: задача поставлена в локальную очередь исполнения.\n"
        f"UTC: {_utc_now()}\n"
        "Статус: queued"
    )
    comment_res = github_api_request("POST", comment_url, token=token, payload={"body": comment})
    if not comment_res.ok:
        raise RuntimeError(f"github_comment_failed:{issue_number}:{comment_res.status}:{comment_res.error_kind or 'unknown'}")


def run_once(config: WorkerConfig) -> dict[str, Any]:
    token = load_github_token()
    if not token:
        raise RuntimeError("missing_github_token")
    processed = _load_state(config.state_file)
    issues = _list_open_issues(config, token=token)
    queued_count = 0
    skipped_count = 0
    for row in issues:
        number = row.get("number")
        if not isinstance(number, int):
            skipped_count += 1
            continue
        if number in processed:
            skipped_count += 1
            continue
        title = str(row.get("title", "")).strip()
        html_url = str(row.get("html_url", "")).strip()
        body = str(row.get("body", "") or "").strip()
        labels = _normalize_labels(row.get("labels"))
        queue_row = {
            "kind": "telegram_github_worker_queue_item",
            "ts_utc": _utc_now(),
            "repo": f"{config.repo_owner}/{config.repo_name}",
            "issue_number": number,
            "issue_url": html_url,
            "title": title,
            "labels": labels,
            "body_preview": body[:500],
            "status": "queued",
        }
        if not config.dry_run:
            _append_jsonl(config.queue_file, queue_row)
            _ensure_issue_claimed(config, token=token, issue_number=number, current_labels=labels)
            processed.add(number)
        queued_count += 1
    if not config.dry_run:
        _save_state(config.state_file, processed=processed, max_items=config.max_state_items)
    return {
        "kind": "telegram_github_worker",
        "status": "pass",
        "repo": f"{config.repo_owner}/{config.repo_name}",
        "labels": config.labels,
        "scanned_open_issues": len(issues),
        "queued_new_issues": queued_count,
        "skipped_known_issues": skipped_count,
        "queue_file": str(config.queue_file),
        "state_file": str(config.state_file),
        "dry_run": config.dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan GitHub issues from Telegram bridge and queue them for execution")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--labels", default="remote,telegram")
    parser.add_argument("--state-file", default="reports/telegram_github_worker_state.json")
    parser.add_argument("--queue-file", default="reports/telegram_github_worker_queue.jsonl")
    parser.add_argument("--max-state-items", default=5000, type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        config = _build_config(args)
        row = run_once(config)
        if args.json:
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(f"queued_new_issues={row['queued_new_issues']} scanned_open_issues={row['scanned_open_issues']}")
        return 0
    except Exception as exc:
        row = {"kind": "telegram_github_worker", "status": "fail", "error": str(exc)}
        if args.json:
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
