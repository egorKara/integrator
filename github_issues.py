from __future__ import annotations

import re
from typing import Any

from github_api import GitHubApiResult, github_api_request


def parse_repo_slug(value: str) -> tuple[str, str] | None:
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


def repo_access(owner: str, repo: str, *, token: str | None) -> GitHubApiResult:
    return github_api_request("GET", f"https://api.github.com/repos/{owner}/{repo}", token=token, payload=None)


def issue_create(
    owner: str,
    repo: str,
    *,
    token: str | None,
    title: str,
    body: str | None,
    labels: list[str] | None,
) -> GitHubApiResult:
    payload: dict[str, Any] = {"title": title}
    if body is not None:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    return github_api_request("POST", f"https://api.github.com/repos/{owner}/{repo}/issues", token=token, payload=payload)


def issue_comment(
    owner: str,
    repo: str,
    *,
    token: str | None,
    number: int,
    body: str,
) -> GitHubApiResult:
    payload: dict[str, Any] = {"body": body}
    return github_api_request(
        "POST",
        f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
        token=token,
        payload=payload,
    )


def issue_close(
    owner: str,
    repo: str,
    *,
    token: str | None,
    number: int,
) -> GitHubApiResult:
    payload: dict[str, Any] = {"state": "closed"}
    return github_api_request("PATCH", f"https://api.github.com/repos/{owner}/{repo}/issues/{number}", token=token, payload=payload)
