from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class StepResult:
    name: str
    ok: bool
    returncode: int
    duration_sec: float
    command: list[str]
    stdout_tail: str
    stderr_tail: str


def _tail(text: str, max_chars: int = 3000) -> str:
    value = text or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def _as_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run_step(name: str, command: list[str], cwd: Path, timeout_sec: int) -> StepResult:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        rc = int(proc.returncode)
        out = proc.stdout or ""
        err = proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = _as_text(exc.stdout)
        err = _as_text(exc.stderr) + f"\nTimed out after {timeout_sec}s"
    duration = time.perf_counter() - start
    return StepResult(
        name=name,
        ok=(rc == 0),
        returncode=rc,
        duration_sec=round(duration, 3),
        command=command,
        stdout_tail=_tail(out),
        stderr_tail=_tail(err),
    )


def _default_report_paths(repo_root: Path, reports_root: Path) -> tuple[Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    day = datetime.now().strftime("%Y-%m-%d")
    out_dir = reports_root / day / "ops"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"ops_checklist_{stamp}.json", out_dir / f"ops_checklist_{stamp}.md"


def _build_markdown(payload: dict) -> str:
    lines: list[str] = []
    lines.append("# Ops Checklist Report")
    lines.append("")
    lines.append(f"- started_at: {payload.get('started_at')}")
    lines.append(f"- finished_at: {payload.get('finished_at')}")
    lines.append(f"- repo_root: {payload.get('repo_root')}")
    lines.append(f"- quick: {payload.get('quick')}")
    lines.append(f"- ok: {payload.get('ok')}")
    lines.append("")
    lines.append("## Steps")
    lines.append("")
    for step in payload.get("steps", []):
        status = "OK" if step.get("ok") else "FAIL"
        lines.append(f"- {step.get('name')}: {status} (rc={step.get('returncode')}, {step.get('duration_sec')}s)")
        lines.append(f"  - cmd: {' '.join(step.get('command', []))}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- stdout/stderr tails are available in JSON report.")
    return "\n".join(lines) + "\n"


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run integrator operational checklist")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent),
        help="Path to repository root (default: script directory parent).",
    )
    parser.add_argument(
        "--reports-root",
        default="reports",
        help="Reports root path (relative to repo root by default).",
    )
    parser.add_argument("--quick", action="store_true", help="Run reduced checklist for faster feedback.")
    parser.add_argument("--no-guardrails", action="store_true", help="Skip guardrails step.")
    parser.add_argument("--no-quality", action="store_true", help="Skip ruff/mypy/unittest steps.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload to stdout.")
    parser.add_argument("--write-report", default="", help="Write JSON report to custom path.")
    parser.add_argument("--timeout-sec", type=int, default=1800, help="Timeout per step in seconds.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    reports_root = Path(args.reports_root)
    if not reports_root.is_absolute():
        reports_root = (repo_root / reports_root).resolve()

    started_at = datetime.now().isoformat(timespec="seconds")

    steps: list[tuple[str, list[str]]] = [
        ("doctor", [sys.executable, "-m", "integrator", "doctor"]),
        ("projects_list", [sys.executable, "-m", "integrator", "projects", "list", "--max-depth", "4"]),
        (
            "agents_only_problems",
            [
                sys.executable,
                "-m",
                "integrator",
                "agents",
                "status",
                "--json",
                "--only-problems",
                "--roots",
                ".\\LocalAI",
                "--max-depth",
                "4",
            ],
        ),
        (
            "algotrading_config_validate",
            [sys.executable, "-m", "integrator", "algotrading", "config", "validate", "--json"],
        ),
    ]

    if not args.no_guardrails:
        steps.append(
            (
                "guardrails_strict",
                [sys.executable, "guardrails.py", "--strict", "--json", "--scan-tracked", "--scan-reports"],
            )
        )

    if not args.no_quality:
        steps.append(("skills_sync", [sys.executable, "-m", "tools.check_skills_sync", "--json"]))
        steps.append(("ruff", [sys.executable, "-m", "ruff", "check", "."]))
        if not args.quick:
            steps.append(("mypy", [sys.executable, "-m", "mypy", "."]))
            steps.append(
                (
                    "unittest",
                    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test*.py"],
                )
            )

    results: list[StepResult] = []
    for name, command in steps:
        result = _run_step(name=name, command=command, cwd=repo_root, timeout_sec=int(args.timeout_sec))
        results.append(result)

    finished_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "kind": "ops_checklist_report",
        "repo_root": str(repo_root),
        "quick": bool(args.quick),
        "started_at": started_at,
        "finished_at": finished_at,
        "ok": all(row.ok for row in results),
        "steps": [asdict(row) for row in results],
    }

    if args.write_report:
        json_path = Path(args.write_report)
        if not json_path.is_absolute():
            json_path = (repo_root / json_path).resolve()
        md_path = json_path.with_suffix(".md")
    else:
        json_path, md_path = _default_report_paths(repo_root=repo_root, reports_root=reports_root)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(payload), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"ok={payload['ok']} report={json_path}")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
