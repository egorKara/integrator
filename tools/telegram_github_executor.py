from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from github_api import github_api_request, load_github_token
from github_issues import parse_repo_slug


@dataclass(frozen=True)
class ExecutorConfig:
    repo_owner: str
    repo_name: str
    state_file: Path
    plans_dir: Path
    max_start_per_cycle: int
    dry_run: bool


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


def _build_config(args: argparse.Namespace) -> ExecutorConfig:
    raw_repo = (args.repo or os.environ.get("TELEGRAM_BRIDGE_REPO") or "").strip()
    slug = parse_repo_slug(raw_repo)
    if slug is None:
        raise RuntimeError("invalid_repo_slug")
    owner, repo = slug
    max_start = int(args.max_start_per_cycle)
    if max_start < 1:
        max_start = 1
    return ExecutorConfig(
        repo_owner=owner,
        repo_name=repo,
        state_file=Path(args.state_file).resolve(),
        plans_dir=Path(args.plans_dir).resolve(),
        max_start_per_cycle=max_start,
        dry_run=bool(args.dry_run),
    )


def _load_started(path: Path) -> set[int]:
    row = _load_json(path)
    if row is None:
        return set()
    raw = row.get("started_issue_numbers")
    if not isinstance(raw, list):
        return set()
    out: set[int] = set()
    for v in raw:
        if isinstance(v, int):
            out.add(v)
    return out


def _save_started(path: Path, started: set[int]) -> None:
    _save_json(
        path,
        {
            "kind": "telegram_github_executor_state",
            "updated_at_utc": _utc_now(),
            "started_issue_numbers": sorted(started)[-5000:],
        },
    )


def _list_queued_issues(config: ExecutorConfig, token: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "state": "open",
            "labels": "remote,telegram,agent:queued",
            "sort": "created",
            "direction": "asc",
            "per_page": 100,
        }
    )
    url = f"https://api.github.com/repos/{config.repo_owner}/{config.repo_name}/issues?{query}"
    res = github_api_request("GET", url, token=token, payload=None)
    if not res.ok or not isinstance(res.json, list):
        raise RuntimeError(f"github_list_failed:{res.status}:{res.error_kind or 'unknown'}")
    out: list[dict[str, Any]] = []
    for row in res.json:
        if isinstance(row, dict) and "pull_request" not in row:
            out.append(row)
    return out


def _labels_from_issue(row: dict[str, Any]) -> list[str]:
    labels_raw = row.get("labels")
    if not isinstance(labels_raw, list):
        return []
    out: list[str] = []
    for x in labels_raw:
        if not isinstance(x, dict):
            continue
        name = x.get("name")
        if isinstance(name, str) and name.strip():
            out.append(name.strip())
    return out


def _extract_request_text(body: str) -> str:
    text = (body or "").strip()
    marker = "Запрос:"
    if marker in text:
        tail = text.split(marker, 1)[1].strip()
        if tail:
            return tail
    return text[:1200]


def _safe_title(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9А-Яа-я._ -]+", "", text).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:60] if cleaned else "issue"


def _write_plan(config: ExecutorConfig, issue_number: int, title: str, request_text: str) -> Path:
    config.plans_dir.mkdir(parents=True, exist_ok=True)
    name = f"issue_{issue_number}_{_safe_title(title)}.md"
    path = config.plans_dir / name
    path.write_text(
        "\n".join(
            [
                f"# Execution plan for issue #{issue_number}",
                "",
                "## Request",
                request_text,
                "",
                "## Initial checklist",
                "- [ ] Снять фактическое состояние по релевантным артефактам",
                "- [ ] Выполнить основной блок задачи",
                "- [ ] Прогнать проверки и зафиксировать результат",
                "- [ ] Обновить issue комментарием с артефактами",
            ]
        ),
        encoding="utf-8",
    )
    return path


def run_once(config: ExecutorConfig) -> dict[str, Any]:
    token = load_github_token()
    if not token:
        raise RuntimeError("missing_github_token")
    started = _load_started(config.state_file)
    queued = _list_queued_issues(config, token=token)
    started_now = 0
    skipped = 0
    for row in queued:
        if started_now >= config.max_start_per_cycle:
            break
        number = row.get("number")
        if not isinstance(number, int):
            skipped += 1
            continue
        if number in started:
            skipped += 1
            continue
        title = str(row.get("title", "")).strip()
        body = str(row.get("body", "") or "")
        request_text = _extract_request_text(body)
        plan_path = _write_plan(config, issue_number=number, title=title, request_text=request_text)
        if not config.dry_run:
            labels = _labels_from_issue(row)
            wanted = list(dict.fromkeys([x for x in labels if x != "agent:queued"] + ["agent:in_progress"]))
            issue_url = f"https://api.github.com/repos/{config.repo_owner}/{config.repo_name}/issues/{number}"
            patch_res = github_api_request("PATCH", issue_url, token=token, payload={"labels": wanted})
            if not patch_res.ok:
                raise RuntimeError(f"github_patch_failed:{number}:{patch_res.status}:{patch_res.error_kind or 'unknown'}")
            comment = (
                "Авто-исполнитель integrator: задача переведена в in-progress.\n"
                f"UTC: {_utc_now()}\n"
                f"Локальный план: {plan_path.as_posix()}"
            )
            comment_res = github_api_request("POST", issue_url + "/comments", token=token, payload={"body": comment})
            if not comment_res.ok:
                raise RuntimeError(f"github_comment_failed:{number}:{comment_res.status}:{comment_res.error_kind or 'unknown'}")
            started.add(number)
        started_now += 1
    if not config.dry_run:
        _save_started(config.state_file, started)
    return {
        "kind": "telegram_github_executor",
        "status": "pass",
        "repo": f"{config.repo_owner}/{config.repo_name}",
        "queued_detected": len(queued),
        "started_now": started_now,
        "skipped": skipped,
        "dry_run": config.dry_run,
        "state_file": str(config.state_file),
        "plans_dir": str(config.plans_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-start queued Telegram GitHub tasks")
    parser.add_argument("--repo", default=None)
    parser.add_argument("--state-file", default="reports/telegram_github_executor_state.json")
    parser.add_argument("--plans-dir", default="reports/telegram_issue_execution_plans")
    parser.add_argument("--max-start-per-cycle", default=1, type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        config = _build_config(args)
        row = run_once(config)
        if args.json:
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(f"started_now={row['started_now']} queued_detected={row['queued_detected']}")
        return 0
    except Exception as exc:
        row = {"kind": "telegram_github_executor", "status": "fail", "error": str(exc)}
        if args.json:
            print(json.dumps(row, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
