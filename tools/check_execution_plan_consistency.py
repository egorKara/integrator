from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

RE_PLAN = re.compile(r"(?P<stem>.+_execution_plan_(?P<date>\d{4}-\d{2}-\d{2}))\.(?P<ext>json|md)$")
REQUIRED_JSON_FIELDS = ("plan_id", "title", "status")


@dataclass(frozen=True, slots=True)
class ConsistencyResult:
    ok: bool
    checked_pairs: list[dict[str, str]]
    errors: list[str]
    checks: list[dict[str, str]]


def _match_plan(path: Path) -> re.Match[str] | None:
    return RE_PLAN.fullmatch(path.name)


def _collect_plans(reports_dir: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    json_map: dict[str, Path] = {}
    md_map: dict[str, Path] = {}
    for path in reports_dir.glob("*_execution_plan_*.json"):
        match = _match_plan(path)
        if match is not None:
            json_map[match.group("stem")] = path
    for path in reports_dir.glob("*_execution_plan_*.md"):
        match = _match_plan(path)
        if match is not None:
            md_map[match.group("stem")] = path
    return json_map, md_map


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"json_payload_not_object:{path.name}")
    return payload


def _resolve_ref(project_root: Path, reports_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    from_project = project_root / candidate
    if from_project.exists():
        return from_project
    return reports_dir / candidate


def check_consistency(reports_dir: Path, date: str | None = None) -> ConsistencyResult:
    json_map, md_map = _collect_plans(reports_dir)
    project_root = reports_dir.parent
    errors: list[str] = []
    checks: list[dict[str, str]] = []
    checked_pairs: list[dict[str, str]] = []

    if date:
        suffix = f"_execution_plan_{date}"
        json_map = {k: v for k, v in json_map.items() if k.endswith(suffix)}
        md_map = {k: v for k, v in md_map.items() if k.endswith(suffix)}

    if not json_map and not md_map:
        raise FileNotFoundError("missing_execution_plan_artifacts")

    json_only = sorted(set(json_map) - set(md_map))
    md_only = sorted(set(md_map) - set(json_map))
    if json_only:
        errors.append(f"orphan_json:{','.join(json_only)}")
    if md_only:
        errors.append(f"orphan_md:{','.join(md_only)}")
    if not json_only and not md_only:
        checks.append({"name": "plan_pairs_present", "status": "pass"})

    for stem in sorted(set(json_map) & set(md_map)):
        json_path = json_map[stem]
        md_path = md_map[stem]
        checked_pairs.append({"stem": stem, "json": str(json_path), "md": str(md_path)})
        match = _match_plan(json_path)
        if match is None:
            errors.append(f"invalid_filename:{json_path.name}")
            continue
        file_date = match.group("date")

        payload = _read_json(json_path)
        missing_fields = [f for f in REQUIRED_JSON_FIELDS if f not in payload]
        if missing_fields:
            errors.append(f"missing_json_fields:{json_path.name}:{','.join(missing_fields)}")
        else:
            checks.append({"name": f"json_required_fields:{json_path.name}", "status": "pass"})

        created_at = str(payload.get("created_at", payload.get("date", ""))).strip()
        if created_at and not created_at.startswith(file_date):
            errors.append(f"date_mismatch_json:{json_path.name}:{created_at}:{file_date}")
        else:
            checks.append({"name": f"json_date_matches_filename:{json_path.name}", "status": "pass"})

        plan_id = str(payload.get("plan_id", "")).strip()
        md_text = md_path.read_text(encoding="utf-8")
        if plan_id and plan_id not in md_text:
            errors.append(f"md_missing_plan_id:{md_path.name}:{plan_id}")
        else:
            checks.append({"name": f"md_plan_id_present:{md_path.name}", "status": "pass"})

        if json_path.name not in md_text:
            errors.append(f"md_missing_json_reference:{md_path.name}:{json_path.name}")
        else:
            checks.append({"name": f"md_json_reference_present:{md_path.name}", "status": "pass"})

        phases = payload.get("phases")
        items = payload.get("items")
        has_work_items = (isinstance(phases, list) and len(phases) > 0) or (isinstance(items, list) and len(items) > 0)
        if not has_work_items:
            errors.append(f"json_missing_work_items:{json_path.name}")
        else:
            checks.append({"name": f"json_work_items_present:{json_path.name}", "status": "pass"})

        source_rfc = str(payload.get("source_rfc", "")).strip()
        source_report = str(payload.get("source_report", "")).strip()
        for raw in (source_rfc, source_report):
            if not raw:
                continue
            target = _resolve_ref(project_root=project_root, reports_dir=reports_dir, value=raw)
            if not target.exists():
                errors.append(f"missing_source_ref:{json_path.name}:{raw}")

    return ConsistencyResult(
        ok=not errors,
        checked_pairs=checked_pairs,
        errors=errors,
        checks=checks,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка согласованности execution plan JSON↔MD")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--date", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    reports_dir = Path(args.reports_dir).resolve()
    try:
        result = check_consistency(reports_dir=reports_dir, date=args.date)
    except Exception as exc:
        payload_fail: dict[str, Any] = {"kind": "execution_plan_consistency", "status": "fail", "errors": [str(exc)]}
        if args.json:
            print(json.dumps(payload_fail, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1

    status = "pass" if result.ok else "fail"
    payload_ok: dict[str, Any] = {
        "kind": "execution_plan_consistency",
        "status": status,
        "checked_pairs": result.checked_pairs,
        "checks": result.checks,
        "errors": result.errors,
    }
    if args.json:
        print(json.dumps(payload_ok, ensure_ascii=False))
    else:
        print(f"pairs={len(result.checked_pairs)}")
        for item in result.checks:
            print(f"CHECK {item['name']}: {item['status']}")
        for error in result.errors:
            print(f"ERROR {error}")
        print(f"STATUS {status}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
