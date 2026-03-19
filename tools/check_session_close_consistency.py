from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

RE_DATE = re.compile(r"session_close_(\d{4}-\d{2}-\d{2})\.(json|md)$")
REQUIRED_JSON_FIELDS = (
    "kind",
    "date",
    "owner",
    "status",
    "scope",
    "thesis",
    "antithesis",
    "synthesis",
    "lessons",
    "next_atomic_step",
    "verification",
    "risks_next",
    "artifacts",
)
REQUIRED_MD_MARKERS = ("## Тезис", "## Антитезис", "## Синтез", "### Уроки", "### Next atomic step")


@dataclass(frozen=True, slots=True)
class ConsistencyResult:
    ok: bool
    date: str
    session_json: Path
    session_md: Path
    errors: list[str]
    checks: list[dict[str, str]]


def _extract_date(path: Path) -> str | None:
    match = RE_DATE.search(path.name)
    if match is None:
        return None
    return match.group(1)


def _resolve_session_files(reports_dir: Path, date: str | None) -> tuple[str, Path, Path]:
    if date:
        json_path = reports_dir / f"session_close_{date}.json"
        md_path = reports_dir / f"session_close_{date}.md"
        if not json_path.exists():
            raise FileNotFoundError(f"missing_json:{json_path}")
        if not md_path.exists():
            raise FileNotFoundError(f"missing_md:{md_path}")
        return date, json_path, md_path

    json_dates: dict[str, Path] = {}
    md_dates: dict[str, Path] = {}
    for path in reports_dir.glob("session_close_*.json"):
        parsed = _extract_date(path)
        if parsed:
            json_dates[parsed] = path
    for path in reports_dir.glob("session_close_*.md"):
        parsed = _extract_date(path)
        if parsed:
            md_dates[parsed] = path
    common_dates = sorted(set(json_dates) & set(md_dates))
    if not common_dates:
        raise FileNotFoundError("missing_session_close_pair")
    latest = common_dates[-1]
    return latest, json_dates[latest], md_dates[latest]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json_payload_not_object")
    return payload


def _resolve_artifact_path(project_root: Path, reports_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    project_candidate = project_root / path
    if project_candidate.exists():
        return project_candidate
    return reports_dir / path


def check_consistency(reports_dir: Path, date: str | None = None) -> ConsistencyResult:
    errors: list[str] = []
    checks: list[dict[str, str]] = []
    project_root = reports_dir.parent
    session_date, session_json, session_md = _resolve_session_files(reports_dir, date)
    checks.append({"name": "session_pair_exists", "status": "pass"})

    payload = _read_json(session_json)
    checks.append({"name": "json_parse", "status": "pass"})

    missing_fields = [field for field in REQUIRED_JSON_FIELDS if field not in payload]
    if missing_fields:
        errors.append(f"missing_json_fields:{','.join(missing_fields)}")
    else:
        checks.append({"name": "json_required_fields", "status": "pass"})

    payload_date = str(payload.get("date", ""))
    if payload_date != session_date:
        errors.append(f"date_mismatch_json:{payload_date}:{session_date}")
    else:
        checks.append({"name": "json_date_matches_filename", "status": "pass"})

    scope = payload.get("scope")
    tracker_ref = ""
    report_ref = ""
    if isinstance(scope, dict):
        tracker_ref = str(scope.get("tracker", "")).strip()
        report_ref = str(scope.get("execution_report", scope.get("report", ""))).strip()
    if not tracker_ref:
        errors.append("scope_tracker_missing")
    if not report_ref:
        errors.append("scope_execution_report_missing")
    if tracker_ref and report_ref:
        checks.append({"name": "scope_references_present", "status": "pass"})

    referenced: list[str] = [str(x) for x in payload.get("artifacts", []) if isinstance(x, str)]
    if tracker_ref:
        referenced.append(tracker_ref)
    if report_ref:
        referenced.append(report_ref)
    unique_refs = sorted(set(ref for ref in referenced if ref.strip()))
    missing_refs: list[str] = []
    for raw in unique_refs:
        target = _resolve_artifact_path(project_root=project_root, reports_dir=reports_dir, value=raw)
        if not target.exists():
            missing_refs.append(raw)
    if missing_refs:
        errors.append(f"missing_referenced_artifacts:{','.join(missing_refs)}")
    else:
        checks.append({"name": "artifacts_exist", "status": "pass"})

    md_text = session_md.read_text(encoding="utf-8")
    missing_markers = [marker for marker in REQUIRED_MD_MARKERS if marker not in md_text]
    if missing_markers:
        errors.append(f"missing_md_markers:{','.join(missing_markers)}")
    else:
        checks.append({"name": "md_sections_present", "status": "pass"})

    if session_date not in md_text:
        errors.append("md_date_marker_missing")
    else:
        checks.append({"name": "md_date_present", "status": "pass"})

    return ConsistencyResult(
        ok=not errors,
        date=session_date,
        session_json=session_json,
        session_md=session_md,
        errors=errors,
        checks=checks,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Проверка согласованности артефактов закрытия сессии")
    parser.add_argument("--reports-dir", default="reports", help="Папка с артефактами reports/")
    parser.add_argument("--date", default=None, help="Дата в формате YYYY-MM-DD (по умолчанию: последняя)")
    parser.add_argument("--json", action="store_true", help="Печатать результат в JSON")
    args = parser.parse_args(list(argv) if argv is not None else None)

    reports_dir = Path(args.reports_dir).resolve()
    try:
        result = check_consistency(reports_dir=reports_dir, date=args.date)
    except Exception as exc:
        if args.json:
            print(
                json.dumps(
                    {
                        "kind": "session_close_consistency",
                        "status": "fail",
                        "errors": [str(exc)],
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(f"FAIL: {exc}")
        return 1

    status = "pass" if result.ok else "fail"
    if args.json:
        print(
            json.dumps(
                {
                    "kind": "session_close_consistency",
                    "status": status,
                    "date": result.date,
                    "session_close_json": str(result.session_json),
                    "session_close_md": str(result.session_md),
                    "checks": result.checks,
                    "errors": result.errors,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(f"session_close_date={result.date}")
        print(f"session_close_json={result.session_json}")
        print(f"session_close_md={result.session_md}")
        for item in result.checks:
            print(f"CHECK {item['name']}: {item['status']}")
        if result.errors:
            for error in result.errors:
                print(f"ERROR {error}")
        print(f"STATUS {status}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
