from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Chain:
    name: str
    description: str
    steps: tuple[tuple[str, ...], ...]


def _default_chains_path() -> Path | None:
    env_path = os.environ.get("INTEGRATOR_CHAINS")
    if env_path:
        return Path(env_path)
    candidate = Path(__file__).with_name("chains.json")
    if candidate.exists():
        return candidate
    return None


def _normalize_steps(value: object) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list):
        return ()
    steps: list[tuple[str, ...]] = []
    for step in value:
        if not isinstance(step, list):
            continue
        parts = [str(item).strip() for item in step if str(item).strip()]
        if parts:
            steps.append(tuple(parts))
    return tuple(steps)


def load_chains(path: Path | None = None) -> list[Chain]:
    target = path or _default_chains_path()
    if not target or not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    chains: list[Chain] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        description = str(item.get("description", "")).strip()
        steps = _normalize_steps(item.get("steps"))
        chains.append(Chain(name=name, description=description, steps=steps))
    return chains


def chain_rows(chains: Iterable[Chain]) -> list[dict[str, object]]:
    return [
        {
            "name": chain.name,
            "description": chain.description,
            "steps": [list(step) for step in chain.steps],
        }
        for chain in chains
    ]
