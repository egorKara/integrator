from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GitHubApiResult:
    ok: bool
    status: int
    json: dict[str, Any] | None
    error_kind: str | None = None
    error: str | None = None


def _default_env_path() -> Path:
    return (Path(__file__).resolve().parent / ".env").resolve()


def _default_token_file() -> Path:
    base = (os.environ.get("INTEGRATOR_SECRETS_DIR") or "").strip()
    if base:
        return (Path(base).expanduser() / "github_token.txt").resolve()
    home = (os.environ.get("USERPROFILE") or os.environ.get("HOME") or "").strip()
    if home:
        return (Path(home) / ".integrator" / "secrets" / "github_token.txt").resolve()
    return (Path.home() / ".integrator" / "secrets" / "github_token.txt").resolve()


def default_github_token_file() -> Path:
    return _default_token_file()


def _load_default_token_file() -> str | None:
    try:
        path = _default_token_file()
    except RuntimeError:
        return None
    try:
        if not path.exists():
            return None
    except OSError:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    token = text.strip()
    return token or None


def _parse_env_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        k = key.strip()
        v = value.strip()
        if not k:
            continue
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        out[k] = v
    return out


def _load_env_file_token() -> str | None:
    env_path = _default_env_path()
    try:
        if not env_path.exists():
            return None
    except OSError:
        return None
    try:
        text = env_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    kv = _parse_env_kv(text)
    token = (kv.get("GITHUB_TOKEN") or kv.get("GH_TOKEN") or "").strip()
    return token or None


def load_github_token() -> str | None:
    token: str | None = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        return token
    token_file = (os.environ.get("GITHUB_TOKEN_FILE") or os.environ.get("INTEGRATOR_GITHUB_TOKEN_FILE") or "").strip()
    if token_file:
        try:
            text = Path(token_file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        token = text.strip()
        if token:
            return token
    token = _load_default_token_file()
    if token:
        return token
    token = _load_env_file_token()
    if token:
        return token
    return None


def github_api_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_api_request(
    method: str,
    url: str,
    *,
    token: str | None,
    payload: dict[str, Any] | None = None,
    timeout_sec: float = 20.0,
) -> GitHubApiResult:
    headers = github_api_headers(token)
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    parsed: dict[str, Any] | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read()
            try:
                parsed = json.loads(body.decode("utf-8", errors="replace"))
            except Exception:
                parsed = None
            return GitHubApiResult(ok=True, status=int(resp.status), json=parsed)
    except urllib.error.HTTPError as e:
        try:
            body = e.read() if hasattr(e, "read") else b""
            try:
                parsed = json.loads(body.decode("utf-8", errors="replace"))
            except Exception:
                parsed = None
            status = int(getattr(e, "code", 0) or 0)
            kind, msg = _classify_github_http_error(status=status, token_present=bool(token))
            return GitHubApiResult(ok=False, status=status, json=parsed, error_kind=kind, error=msg)
        finally:
            try:
                e.close()
            except Exception:
                pass
    except Exception as e:
        return GitHubApiResult(ok=False, status=0, json=None, error_kind="network_error", error=str(e))


def _classify_github_http_error(*, status: int, token_present: bool) -> tuple[str, str]:
    if status in (401, 403):
        return "auth_error", "GitHub API отклонил запрос: проверьте токен и его права."
    if status == 404 and not token_present:
        return "auth_missing", "GitHub API вернул 404 без аутентификации (приватные репозитории маскируются как 404)."
    if status == 404 and token_present:
        return "not_found_or_authz", "GitHub API вернул 404: проверьте owner/repo и доступ токена к репозиторию."
    return "http_error", f"GitHub API вернул HTTP {status}."
