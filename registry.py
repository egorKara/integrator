from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    name: str
    root: str
    status: str
    priority: str
    entrypoint: str
    tags: tuple[str, ...]


def _default_registry_path() -> Path | None:
    env_path = os.environ.get("INTEGRATOR_REGISTRY")
    if env_path:
        return Path(env_path)
    candidate = Path(__file__).with_name("registry.json")
    if candidate.exists():
        return candidate
    return None


def _normalize_tags(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    items = [str(item).strip() for item in value if str(item).strip()]
    return tuple(items)


def load_registry(path: Path | None = None) -> list[RegistryEntry]:
    target = path or _default_registry_path()
    if not target or not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    entries: list[RegistryEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        root = str(item.get("root", "")).strip()
        if not name or not root:
            continue
        status = str(item.get("status", "")).strip()
        priority = str(item.get("priority", "")).strip()
        entrypoint = str(item.get("entrypoint", "")).strip()
        tags = _normalize_tags(item.get("tags"))
        entries.append(
            RegistryEntry(
                name=name,
                root=root,
                status=status,
                priority=priority,
                entrypoint=entrypoint,
                tags=tags,
            )
        )
    return entries


def registry_rows(entries: Iterable[RegistryEntry]) -> list[dict[str, object]]:
    return [
        {
            "name": entry.name,
            "root": entry.root,
            "status": entry.status,
            "priority": entry.priority,
            "entrypoint": entry.entrypoint,
            "tags": list(entry.tags),
        }
        for entry in entries
    ]


def registry_roots(entries: Iterable[RegistryEntry]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for entry in entries:
        path = Path(entry.root)
        if path in seen:
            continue
        seen.add(path)
        roots.append(path)
    return roots
