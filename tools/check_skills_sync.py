from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

INDEX_PATH = Path("docs/SKILLS_INDEX.md")
AGENTS_PATH = Path("AGENTS.md")
MAP_ROOT_PATH = Path(".agents/skills/skills_map.json")
MAP_ASSISTANT_PATH = Path("LocalAI/assistant/.agents/skills/skills_map.json")


@dataclass(frozen=True, slots=True)
class SkillsSyncResult:
    ok: bool
    checks: list[dict[str, Any]]
    errors: list[str]
    counts: dict[str, int]


def _parse_index_rows(index_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw_line in index_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        if re.fullmatch(r"\|\s*-+\s*(\|\s*-+\s*)+\|?", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        if cells[0] == "skill":
            continue
        rows.append(
            {
                "skill": cells[0],
                "scope": cells[1],
                "trigger": cells[2],
                "anti_trigger": cells[3],
                "owner": cells[4],
                "path": cells[5].strip("`"),
                "security_gate": cells[6],
            }
        )
    return rows


def _extract_skill_routing_names(agents_text: str) -> set[str]:
    section_match = re.search(r"^## Skill Routing\s*$([\s\S]*?)(?:^##\s+|\Z)", agents_text, flags=re.MULTILINE)
    if not section_match:
        return set()
    body = section_match.group(1)
    names = re.findall(r"-\s+`([a-z0-9-]+)`\s*:", body)
    return set(names)


def _collect_skill_files(project_root: Path) -> dict[str, Path]:
    paths = list(project_root.glob(".trae/skills/*/SKILL.md"))
    paths.extend(project_root.glob("LocalAI/assistant/.trae/skills/*/SKILL.md"))
    result: dict[str, Path] = {}
    for path in paths:
        result[path.parent.name] = path
    return result


def _load_map(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_map_payload:{path}")
    return payload


def check_sync(project_root: Path) -> SkillsSyncResult:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    index_file = project_root / INDEX_PATH
    agents_file = project_root / AGENTS_PATH
    map_root_file = project_root / MAP_ROOT_PATH
    map_assistant_file = project_root / MAP_ASSISTANT_PATH

    for required in (index_file, agents_file, map_root_file, map_assistant_file):
        if not required.exists():
            errors.append(f"missing_required_file:{required.relative_to(project_root)}")

    if errors:
        return SkillsSyncResult(ok=False, checks=checks, errors=errors, counts={})

    index_rows = _parse_index_rows(index_file.read_text(encoding="utf-8"))
    if not index_rows:
        errors.append("index_rows_missing")

    index_names: list[str] = [row["skill"] for row in index_rows]
    index_set = set(index_names)
    if len(index_set) != len(index_names):
        errors.append("index_duplicate_skills")
    else:
        checks.append({"name": "index_unique_skills", "status": "pass"})

    skill_files = _collect_skill_files(project_root)
    fs_set = set(skill_files.keys())
    if index_set != fs_set:
        missing_in_index = sorted(fs_set - index_set)
        missing_in_fs = sorted(index_set - fs_set)
        if missing_in_index:
            errors.append(f"missing_in_index:{','.join(missing_in_index)}")
        if missing_in_fs:
            errors.append(f"missing_skill_file:{','.join(missing_in_fs)}")
    else:
        checks.append({"name": "index_matches_skill_files", "status": "pass"})

    for row in index_rows:
        skill_name = row["skill"]
        skill_path = project_root / Path(row["path"])
        if not skill_path.exists():
            errors.append(f"index_path_missing:{skill_name}:{row['path']}")
    if not any(err.startswith("index_path_missing:") for err in errors):
        checks.append({"name": "index_paths_exist", "status": "pass"})

    payload_root = _load_map(map_root_file)
    payload_assistant = _load_map(map_assistant_file)
    map_entries_root = payload_root.get("mappings", []) if isinstance(payload_root.get("mappings", []), list) else []
    map_entries_assistant = (
        payload_assistant.get("mappings", []) if isinstance(payload_assistant.get("mappings", []), list) else []
    )
    map_entries = [entry for entry in [*map_entries_root, *map_entries_assistant] if isinstance(entry, dict)]
    map_names = [str(entry.get("name", "")).strip() for entry in map_entries if str(entry.get("name", "")).strip()]
    map_set = set(map_names)
    if len(map_set) != len(map_names):
        errors.append("map_duplicate_skill_names")
    else:
        checks.append({"name": "maps_unique_skills", "status": "pass"})

    if map_set != index_set:
        missing_in_map = sorted(index_set - map_set)
        missing_in_index_by_map = sorted(map_set - index_set)
        if missing_in_map:
            errors.append(f"missing_in_maps:{','.join(missing_in_map)}")
        if missing_in_index_by_map:
            errors.append(f"missing_in_index_by_maps:{','.join(missing_in_index_by_map)}")
    else:
        checks.append({"name": "maps_match_index", "status": "pass"})

    for entry in map_entries_root:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        canonical = str(entry.get("canonical_path", "")).strip()
        target = project_root / canonical
        if not canonical or not target.exists():
            errors.append(f"map_canonical_missing:root:{name}:{canonical}")
    for entry in map_entries_assistant:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", "")).strip()
        canonical = str(entry.get("canonical_path", "")).strip()
        target = project_root / "LocalAI/assistant" / canonical
        if not canonical or not target.exists():
            errors.append(f"map_canonical_missing:assistant:{name}:{canonical}")
    if not any(err.startswith("map_canonical_missing:") for err in errors):
        checks.append({"name": "map_canonical_paths_exist", "status": "pass"})

    agents_names = _extract_skill_routing_names(agents_file.read_text(encoding="utf-8"))
    if not agents_names:
        errors.append("agents_skill_routing_missing")
    elif agents_names != index_set:
        missing_in_agents = sorted(index_set - agents_names)
        missing_in_index_by_agents = sorted(agents_names - index_set)
        if missing_in_agents:
            errors.append(f"missing_in_agents:{','.join(missing_in_agents)}")
        if missing_in_index_by_agents:
            errors.append(f"missing_in_index_by_agents:{','.join(missing_in_index_by_agents)}")
    else:
        checks.append({"name": "agents_match_index", "status": "pass"})

    counts = {
        "index_skills": len(index_set),
        "skill_files": len(fs_set),
        "map_skills": len(map_set),
        "agents_skills": len(agents_names),
    }
    return SkillsSyncResult(ok=not errors, checks=checks, errors=errors, counts=counts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка синхронизации SKILLS_INDEX, skills_map и AGENTS")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).resolve()
    try:
        result = check_sync(project_root=root)
    except Exception as exc:
        payload_fail: dict[str, Any] = {"kind": "skills_sync", "status": "fail", "errors": [str(exc)]}
        if args.json:
            print(json.dumps(payload_fail, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1

    payload: dict[str, Any] = {
        "kind": "skills_sync",
        "status": "pass" if result.ok else "fail",
        "checks": result.checks,
        "errors": result.errors,
        "counts": result.counts,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for check in result.checks:
            print(f"CHECK {check['name']}: {check['status']}")
        for error in result.errors:
            print(f"ERROR {error}")
        print(f"COUNTS {result.counts}")
        print(f"STATUS {payload['status']}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
