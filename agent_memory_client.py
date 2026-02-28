from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable

from agent_memory_routes import resolve_route


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: bytes
    json: dict[str, Any] | None


def _join_url(base_url: str, path: str) -> str:
    base = (base_url or "").rstrip("/")
    if not base:
        raise ValueError("base_url required")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _read_text(path: str, max_chars: int | None = None) -> str:
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    if max_chars is not None and max_chars >= 0:
        return text[:max_chars]
    return text


def _url_with_query(base_url: str, path: str, params: dict[str, object]) -> str:
    url = _join_url(base_url, path)
    query: dict[str, str] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            if v:
                query[k] = "1"
            continue
        query[k] = str(v)
    if not query:
        return url
    return url + "?" + urllib.parse.urlencode(query)


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    auth_token: str | None,
    timeout_sec: float = 10.0,
) -> HttpResult:
    headers = {"Accept": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

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
            return HttpResult(status=int(resp.status), body=body, json=parsed)
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        try:
            parsed = json.loads(body.decode("utf-8", errors="replace"))
        except Exception:
            parsed = None
        return HttpResult(status=int(getattr(e, "code", 0) or 0), body=body, json=parsed)


def memory_write(
    base_url: str,
    summary: str,
    content: str,
    *,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
    kind: str = "event",
    tags: Iterable[str] | None = None,
    source: str | None = None,
    importance: float | None = None,
    success: bool | None = None,
    metadata: dict[str, Any] | None = None,
    ttl_sec: int | None = None,
    author: str | None = None,
    module: str | None = None,
    trust: float | None = None,
    confirm_procedure: bool = False,
) -> HttpResult:
    url = _join_url(base_url, resolve_route(routes, "memory_write"))
    payload: dict[str, Any] = {
        "summary": summary,
        "content": content,
        "kind": kind,
        "tags": list(tags or []),
        "source": source,
        "importance": importance,
        "success": success,
        "metadata": metadata or {},
        "ttl_sec": ttl_sec,
        "author": author,
        "module": module,
        "trust": trust,
        "confirm_procedure": bool(confirm_procedure),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    return _http_json("POST", url, payload, auth_token=auth_token)


def memory_search(
    base_url: str,
    q: str,
    *,
    limit: int = 10,
    kind: str | None = None,
    min_importance: float | None = None,
    include_quarantined: bool = False,
    include_deleted: bool = False,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
) -> HttpResult:
    params: dict[str, object] = {
        "q": q,
        "limit": int(limit),
        "kind": kind,
        "min_importance": min_importance,
        "include_quarantined": bool(include_quarantined),
        "include_deleted": bool(include_deleted),
    }
    url = _url_with_query(base_url, resolve_route(routes, "memory_search"), params)
    return _http_json("GET", url, payload=None, auth_token=auth_token)


def memory_recent(
    base_url: str,
    *,
    limit: int = 10,
    kind: str | None = None,
    include_quarantined: bool = False,
    include_deleted: bool = False,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
) -> HttpResult:
    params: dict[str, object] = {
        "limit": int(limit),
        "kind": kind,
        "include_quarantined": bool(include_quarantined),
        "include_deleted": bool(include_deleted),
    }
    url = _url_with_query(base_url, resolve_route(routes, "memory_recent"), params)
    return _http_json("GET", url, payload=None, auth_token=auth_token)


def memory_retrieve(
    base_url: str,
    *,
    q: str | None = None,
    limit: int = 10,
    kind: str | None = None,
    module: str | None = None,
    min_trust: float | None = None,
    max_age_sec: int | None = None,
    include_quarantined: bool = False,
    include_deleted: bool = False,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
) -> HttpResult:
    params: dict[str, object] = {
        "q": q,
        "limit": int(limit),
        "kind": kind,
        "module": module,
        "min_trust": min_trust,
        "max_age_sec": max_age_sec,
        "include_quarantined": bool(include_quarantined),
        "include_deleted": bool(include_deleted),
    }
    url = _url_with_query(base_url, resolve_route(routes, "memory_retrieve"), params)
    return _http_json("GET", url, payload=None, auth_token=auth_token)


def memory_stats(
    base_url: str,
    *,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
) -> HttpResult:
    url = _join_url(base_url, resolve_route(routes, "memory_stats"))
    return _http_json("GET", url, payload=None, auth_token=auth_token)


def memory_feedback(
    base_url: str,
    memory_id: int,
    rating: int,
    *,
    notes: str | None = None,
    auth_token: str | None = None,
    routes: dict[str, str] | None = None,
) -> HttpResult:
    url = _join_url(base_url, resolve_route(routes, "memory_feedback"))
    payload: dict[str, Any] = {"id": int(memory_id), "rating": int(rating), "notes": notes}
    payload = {k: v for k, v in payload.items() if v is not None}
    return _http_json("POST", url, payload, auth_token=auth_token)


def memory_write_file(
    base_url: str,
    summary: str,
    content_path: str,
    *,
    auth_token: str | None = None,
    chunk_size: int = 20000,
    **kwargs: Any,
) -> list[HttpResult]:
    if chunk_size <= 0:
        chunk_size = 20000
    full = _read_text(content_path)
    chunks = [full[i : i + chunk_size] for i in range(0, len(full), chunk_size)] or [""]
    total = len(chunks)
    results: list[HttpResult] = []
    for idx, chunk in enumerate(chunks, start=1):
        part_summary = summary
        if total > 1:
            part_summary = f"{summary} (part {idx}/{total})"
        meta = dict(kwargs.get("metadata") or {})
        meta["source_path"] = content_path
        meta["chunk_index"] = idx
        meta["chunk_total"] = total
        kwargs2 = dict(kwargs)
        kwargs2["metadata"] = meta
        results.append(
            memory_write(
                base_url,
                part_summary,
                chunk,
                auth_token=auth_token,
                **kwargs2,
            )
        )
    return results
