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


def _ruleset_payload(branch: str) -> dict[str, Any]:
    return {
        "name": "integrator-main-protection",
        "target": "branch",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": [f"refs/heads/{branch}"], "exclude": []}},
        "rules": [
            {
                "type": "required_linear_history",
            },
            {
                "type": "pull_request",
                "parameters": {
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": True,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 2,
                    "required_review_thread_resolution": True,
                },
            },
        ],
    }


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
    results: dict[str, Any] = {
        "kind": "branch_protection_apply",
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "timestamp": _timestamp(),
        "checks": {},
    }

    def _write_report() -> Path:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        out = reports_dir / f"branch_protection_apply_{results['timestamp']}.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return out

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
        out_path = _write_report()
        print(str(out_path))
        return 1

    if check_only:
        out_path = _write_report()
        print(str(out_path))
        return 0

    repo_visibility = ""
    if isinstance(repo_access.json, dict):
        repo_visibility = str(repo_access.json.get("visibility", "")).strip().lower()
    if repo_visibility == "private":
        results["checks"]["precondition_visibility"] = {
            "ok": False,
            "status": 403,
            "json": {"visibility": "private"},
            "error_kind": "feature_unavailable_plan",
            "error": "Репозиторий private: для branch protection на текущем тарифе сначала переведите репозиторий в public.",
        }
        out_path = _write_report()
        print(str(out_path))
        return 1

    rulesets_url = f"https://api.github.com/repos/{owner}/{repo}/rulesets"
    list_rulesets = github_api_request("GET", rulesets_url, token=token, payload=None)
    results["checks"]["list_rulesets"] = dict(list_rulesets.__dict__)
    existing_ruleset_id: int | None = None
    if list_rulesets.ok and isinstance(list_rulesets.json, list):
        for item in list_rulesets.json:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")) == "integrator-main-protection":
                rid = item.get("id")
                if isinstance(rid, int):
                    existing_ruleset_id = rid
                    break
    rules_payload = _ruleset_payload(branch)
    if existing_ruleset_id is not None:
        apply_ruleset = github_api_request(
            "PUT",
            f"{rulesets_url}/{existing_ruleset_id}",
            token=token,
            payload=rules_payload,
        )
    else:
        apply_ruleset = github_api_request(
            "POST",
            rulesets_url,
            token=token,
            payload=rules_payload,
        )
    results["checks"]["apply_ruleset"] = dict(apply_ruleset.__dict__)
    if existing_ruleset_id is not None:
        results["checks"]["read_ruleset"] = dict(
            github_api_request(
                "GET",
                f"{rulesets_url}/{existing_ruleset_id}",
                token=token,
                payload=None,
            ).__dict__
        )

    out_path = _write_report()
    print(str(out_path))

    checks = results["checks"]
    if isinstance(checks.get("apply_ruleset"), dict):
        ok = bool(checks.get("repo_access", {}).get("ok")) and bool(checks.get("apply_ruleset", {}).get("ok"))
    else:
        ok = all(bool(v.get("ok")) for v in checks.values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
