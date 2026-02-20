from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _parse_repo_slug(value: str) -> tuple[str, str] | None:
    v = (value or "").strip()
    if not v:
        return None

    if re.fullmatch(r"[^/]+/[^/]+", v):
        owner, repo = v.split("/", 1)
        return owner, repo

    if v.startswith("git@github.com:"):
        v = v[len("git@github.com:") :]
    if v.startswith("https://github.com/"):
        v = v[len("https://github.com/") :]

    v = v.rstrip("/")
    if v.endswith(".git"):
        v = v[: -len(".git")]

    if "/" not in v:
        return None
    owner, repo = v.split("/", 1)
    if owner and repo:
        return owner, repo
    return None


def _api_request(method: str, url: str, token: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20.0) as resp:
            body = resp.read()
            try:
                parsed = json.loads(body.decode("utf-8", errors="replace"))
            except Exception:
                parsed = None
            return {"ok": True, "status": int(resp.status), "json": parsed}
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
        except Exception:
            parsed = None
        return {"ok": False, "status": int(getattr(e, "code", 0) or 0), "json": parsed}
    except Exception as e:
        return {"ok": False, "status": 0, "json": {"error": str(e)}}


def main(argv: list[str]) -> int:
    repo_env = os.environ.get("GITHUB_REPOSITORY") or ""
    owner_env = os.environ.get("GITHUB_OWNER") or ""
    name_env = os.environ.get("GITHUB_REPO") or ""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
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

    results["checks"]["required_status_checks"] = _api_request(
        "PUT",
        base + "/required_status_checks",
        token,
        {"strict": True, "contexts": ["ci / test"]},
    )
    results["checks"]["required_pull_request_reviews"] = _api_request(
        "PUT",
        base + "/required_pull_request_reviews",
        token,
        {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
            "required_approving_review_count": 2,
        },
    )
    results["checks"]["enforce_admins"] = _api_request("POST", base + "/enforce_admins", token, None)

    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"branch_protection_apply_{results['timestamp']}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))

    ok = all(bool(v.get("ok")) for v in results["checks"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
