from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _parse_repo_slug(value: str) -> tuple[str, str] | None:
    v = (value or "").strip()
    if not v:
        return None

    if v.startswith("git@github.com:"):
        v = v[len("git@github.com:") :]
    if v.startswith("https://github.com/"):
        v = v[len("https://github.com/") :]

    v = v.rstrip("/")
    if v.endswith(".git"):
        v = v[: -len(".git")]

    if re.fullmatch(r"[^/]+/[^/]+", v):
        owner, repo = v.split("/", 1)
        return owner, repo

    if "/" not in v:
        return None
    owner, repo = v.split("/", 1)
    if owner and repo:
        return owner, repo
    return None


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from github_api import github_api_request, load_github_token

    check_only = "--check-only" in set(argv[1:])

    repo_env = os.environ.get("GITHUB_REPOSITORY") or ""
    owner_env = os.environ.get("GITHUB_OWNER") or ""
    name_env = os.environ.get("GITHUB_REPO") or ""
    token = load_github_token() or ""
    branch = os.environ.get("GITHUB_BRANCH") or "main"

    slug = _parse_repo_slug(repo_env) or (_parse_repo_slug(f"{owner_env}/{name_env}") if owner_env and name_env else None)
    if not slug:
        print("repo not specified (set GITHUB_REPOSITORY=owner/repo)", file=sys.stderr)
        return 2
    if not token:
        print("token not specified (set GITHUB_TOKEN)", file=sys.stderr)
        return 2

    owner, repo = slug
    base = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"

    results: dict[str, Any] = {
        "kind": "branch_protection_apply",
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "timestamp": _timestamp(),
        "checks": {},
    }

    repo_access = github_api_request(
        "GET",
        f"https://api.github.com/repos/{owner}/{repo}",
        token=token,
        payload=None,
    )
    results["checks"]["repo_access"] = dict(repo_access.__dict__)
    if not repo_access.ok:
        if repo_access.error:
            print(repo_access.error, file=sys.stderr)
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"branch_protection_apply_{results['timestamp']}.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(out_path))
        return 1

    if check_only:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"branch_protection_apply_{results['timestamp']}.json"
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(str(out_path))
        return 0

    results["checks"]["required_status_checks"] = dict(
        github_api_request(
            "PUT",
            base + "/required_status_checks",
            token=token,
            payload={"strict": True, "contexts": ["ci / test"]},
        ).__dict__
    )
    results["checks"]["required_pull_request_reviews"] = dict(
        github_api_request(
            "PUT",
            base + "/required_pull_request_reviews",
            token=token,
            payload={
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": True,
                "required_approving_review_count": 2,
            },
        ).__dict__
    )
    results["checks"]["enforce_admins"] = dict(
        github_api_request(
            "POST",
            base + "/enforce_admins",
            token=token,
            payload=None,
        ).__dict__
    )

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"branch_protection_apply_{results['timestamp']}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))

    ok = all(bool(v.get("ok")) for v in results["checks"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
