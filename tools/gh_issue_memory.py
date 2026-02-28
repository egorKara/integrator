from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="gh_issue_memory.py")
    p.add_argument("--repo", default=None)
    p.add_argument("--dry-run", action="store_true")

    sub = p.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--body-file", default=None)
    create.add_argument("--labels", nargs="*", default=[])

    comment = sub.add_parser("comment")
    comment.add_argument("--issue", type=int, required=True)
    comment.add_argument("--body-file", required=True)

    close = sub.add_parser("close")
    close.add_argument("--issue", type=int, required=True)

    return p.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from github_api import load_github_token
    from github_issues import issue_close, issue_comment, issue_create, parse_repo_slug, repo_access

    args = _parse_args(argv)
    token = load_github_token()

    repo_env = os.environ.get("GITHUB_REPOSITORY") or ""
    owner_env = os.environ.get("GITHUB_OWNER") or ""
    name_env = os.environ.get("GITHUB_REPO") or ""

    slug = parse_repo_slug(str(args.repo or "").strip()) if args.repo else None
    slug = slug or parse_repo_slug(repo_env) or (parse_repo_slug(f"{owner_env}/{name_env}") if owner_env and name_env else None)
    if not slug:
        print("repo not specified (set GITHUB_REPOSITORY=owner/repo or pass --repo)", file=sys.stderr)
        return 2

    owner, repo = slug
    ts = _timestamp()
    report: dict[str, Any] = {
        "kind": "gh_issue_memory",
        "timestamp": ts,
        "repo": f"{owner}/{repo}",
        "cmd": str(args.cmd),
        "dry_run": bool(args.dry_run),
        "token_present": bool(token),
    }

    if bool(args.dry_run):
        if args.cmd == "create":
            body = _read_text(args.body_file) if args.body_file else None
            report["plan"] = {
                "method": "POST",
                "url": f"https://api.github.com/repos/{owner}/{repo}/issues",
                "title_len": len(str(args.title)),
                "body_chars": len(body or ""),
                "labels": list(args.labels or []),
            }
        elif args.cmd == "comment":
            body = _read_text(args.body_file)
            report["plan"] = {
                "method": "POST",
                "url": f"https://api.github.com/repos/{owner}/{repo}/issues/{int(args.issue)}/comments",
                "body_chars": len(body),
            }
        elif args.cmd == "close":
            report["plan"] = {
                "method": "PATCH",
                "url": f"https://api.github.com/repos/{owner}/{repo}/issues/{int(args.issue)}",
                "payload": {"state": "closed"},
            }
        else:
            print("unknown command", file=sys.stderr)
            return 2
        _write_report(ts, report)
        print(str(_report_path(ts)))
        return 0

    if not token:
        print("token not specified (set GITHUB_TOKEN/GH_TOKEN or *_TOKEN_FILE)", file=sys.stderr)
        return 2

    access = repo_access(owner, repo, token=token)
    report["repo_access"] = dict(access.__dict__)
    if not access.ok:
        if access.error:
            print(access.error, file=sys.stderr)
        _write_report(ts, report)
        return 1

    if args.cmd == "create":
        body = _read_text(args.body_file) if args.body_file else None
        plan = {
            "method": "POST",
            "url": f"https://api.github.com/repos/{owner}/{repo}/issues",
            "title_len": len(str(args.title)),
            "body_chars": len(body or ""),
            "labels": list(args.labels or []),
        }
        report["plan"] = plan
        if bool(args.dry_run):
            _write_report(ts, report)
            print(str(_report_path(ts)))
            return 0
        res = issue_create(owner, repo, token=token, title=str(args.title), body=body, labels=list(args.labels or []))
        report["result"] = dict(res.__dict__)
        if res.json and isinstance(res.json.get("number"), int):
            report["issue_number"] = int(res.json["number"])
        if res.json and isinstance(res.json.get("html_url"), str):
            report["issue_url"] = str(res.json["html_url"])
        _write_report(ts, report)
        print(str(_report_path(ts)))
        return 0 if res.ok else 1

    if args.cmd == "comment":
        body = _read_text(args.body_file)
        plan = {
            "method": "POST",
            "url": f"https://api.github.com/repos/{owner}/{repo}/issues/{int(args.issue)}/comments",
            "body_chars": len(body),
        }
        report["plan"] = plan
        if bool(args.dry_run):
            _write_report(ts, report)
            print(str(_report_path(ts)))
            return 0
        res = issue_comment(owner, repo, token=token, number=int(args.issue), body=body)
        report["result"] = dict(res.__dict__)
        _write_report(ts, report)
        print(str(_report_path(ts)))
        return 0 if res.ok else 1

    if args.cmd == "close":
        plan = {
            "method": "PATCH",
            "url": f"https://api.github.com/repos/{owner}/{repo}/issues/{int(args.issue)}",
            "payload": {"state": "closed"},
        }
        report["plan"] = plan
        if bool(args.dry_run):
            _write_report(ts, report)
            print(str(_report_path(ts)))
            return 0
        res = issue_close(owner, repo, token=token, number=int(args.issue))
        report["result"] = dict(res.__dict__)
        _write_report(ts, report)
        print(str(_report_path(ts)))
        return 0 if res.ok else 1

    print("unknown command", file=sys.stderr)
    return 2


def _report_path(ts: str) -> Path:
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir / f"gh_issue_memory_{ts}.json"


def _write_report(ts: str, report: dict[str, Any]) -> None:
    _report_path(ts).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
