from __future__ import annotations

import json
from pathlib import Path


DEFAULT_AGENT_MEMORY_ROUTES: dict[str, str] = {
    "memory_write": "/agent/memory/write",
    "memory_search": "/agent/memory/search",
    "memory_recent": "/agent/memory/recent",
    "memory_retrieve": "/agent/memory/retrieve",
    "memory_stats": "/agent/memory/stats",
    "memory_feedback": "/agent/memory/feedback",
}


def load_gateway_routes(gateway_json_path: str) -> dict[str, str]:
    p = Path(gateway_json_path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return dict(DEFAULT_AGENT_MEMORY_ROUTES)
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return dict(DEFAULT_AGENT_MEMORY_ROUTES)
    if not isinstance(raw, dict):
        return dict(DEFAULT_AGENT_MEMORY_ROUTES)
    routes = raw.get("routes")
    if not isinstance(routes, dict):
        return dict(DEFAULT_AGENT_MEMORY_ROUTES)
    out = dict(DEFAULT_AGENT_MEMORY_ROUTES)
    for k in out.keys():
        v = routes.get(k)
        if isinstance(v, str) and v.strip().startswith("/"):
            out[k] = v.strip()
    return out


def resolve_route(routes: dict[str, str] | None, key: str) -> str:
    merged = routes or DEFAULT_AGENT_MEMORY_ROUTES
    value = merged.get(key)
    if isinstance(value, str) and value.strip().startswith("/"):
        return value.strip()
    return DEFAULT_AGENT_MEMORY_ROUTES[key]
