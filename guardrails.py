from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

TEXT_EXTENSIONS = {
    ".py",
    ".ps1",
    ".psm1",
    ".psd1",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".sh",
    ".bat",
    ".cmd",
}

ABS_PATH_SCAN_EXTENSIONS = {
    ".py",
    ".ps1",
    ".psm1",
    ".psd1",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".ini",
    ".cfg",
    ".sh",
    ".bat",
    ".cmd",
}

SECRET_SCAN_EXTENSIONS = {
    ".md",
    ".txt",
    ".log",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
}

SECRET_SCAN_MAX_BYTES = 2_000_000

EXCLUDED_DIR_PARTS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "env312",
    ".venv_indexer",
    "deps_backup",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    ".tmp",
    "LocalAI/backups",
    "LocalAI/tools",
    "reports",
}

SCANNED_SUBDIRS = (
    "scripts",
    "tools",
    "tests",
    ".github/workflows",
)

ALGO_REQUIRED_FILES = (
    "README.md",
    "00-Rules (Summary).md",
    ".trae/rules/project_rules.md",
    "Specs/SPEC-001-Pipeline.md",
    "Configs/algotrading.json",
)

PROJECT_REQUIRED_BY_NAME: dict[str, tuple[str, ...]] = {
    "AlgoTrading": ALGO_REQUIRED_FILES,
    "stealth-nexus": ("00-Rules (Summary).md", ".trae/rules/project_rules.md"),
    "vpn-manager": (
        "00-Rules (Summary).md",
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODING_STYLE.md",
    ),
}

PROJECT_OPTIONAL_DOCS = (
    "README.md",
    "00-Rules (Summary).md",
    ".trae/rules/project_rules.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODING_STYLE.md",
)

SECRET_ERROR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PRIVATE) PRIVATE KEY-----"),
    ),
)

SECRET_WARN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "generic_secret_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*['\"][^'\"]{16,}['\"]"
        ),
    ),
)

RISKY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("git_reset_hard", re.compile(r"(?i)\bgit\s+reset\s+--hard\b")),
    ("rm_rf_root", re.compile(r"(?i)\brm\s+-rf\s+/\b")),
    (
        "powershell_remove_system_drive",
        re.compile(
            r"(?i)\bRemove-Item\b[^\n\r]*\b-Recurse\b[^\n\r]*\b-Force\b[^\n\r]*[\"']?C:\\"
        ),
    ),
    ("net_disable", re.compile(r"(?i)\bDisable-NetAdapter\b")),
    ("route_delete_default", re.compile(r"(?i)\broute\s+delete\s+0\.0\.0\.0\b")),
    (
        "netsh_disable_interface",
        re.compile(r"(?i)\bnetsh\s+interface\s+set\s+interface\b[^\n\r]*\bdisable\b"),
    ),
    ("format_volume", re.compile(r"(?i)\bFormat-Volume\b")),
)

ABSOLUTE_USER_PATH_PATTERN = re.compile(r"(?i)\b[A-Z]:\\Users\\")


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    severity: str = "error"


def _is_binary_by_extension(path: Path) -> bool:
    return path.suffix.lower() not in TEXT_EXTENSIONS


def _path_contains_excluded_part(path: Path, repo_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
        rel_text = str(rel).replace("\\", "/")
    except Exception:
        rel_text = str(path).replace("\\", "/")
    parts = set(rel_text.split("/"))
    if parts.intersection(EXCLUDED_DIR_PARTS):
        return True
    for ex in EXCLUDED_DIR_PARTS:
        if "/" in ex and rel_text.startswith(ex + "/"):
            return True
    return False


def _iter_default_scan_files(repo_root: Path) -> Iterable[Path]:
    seen: set[str] = set()

    for path in repo_root.iterdir():
        if not path.is_file():
            continue
        if _is_binary_by_extension(path) or _path_contains_excluded_part(path, repo_root):
            continue
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            yield path

    for rel_dir in SCANNED_SUBDIRS:
        base = repo_root / rel_dir
        if not base.exists() or not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if _is_binary_by_extension(path) or _path_contains_excluded_part(path, repo_root):
                continue
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                yield path

    projects_root = repo_root / "vault" / "Projects"
    if projects_root.exists() and projects_root.is_dir():
        for project in projects_root.iterdir():
            if not project.is_dir():
                continue
            for rel_doc in PROJECT_OPTIONAL_DOCS:
                p = project / rel_doc
                if p.exists() and p.is_file() and not _is_binary_by_extension(p):
                    key = str(p.resolve())
                    if key not in seen:
                        seen.add(key)
                        yield p


def _resolve_input_paths(repo_root: Path, raw_paths: Sequence[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in raw_paths:
        p = Path(raw)
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        else:
            p = p.resolve()
        if p.exists() and p.is_file() and not _is_binary_by_extension(p):
            resolved.append(p)
    return resolved


def _check_core_roots(repo_root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    required = {
        "repo_root": repo_root,
        "vault_root": repo_root / "vault",
        "vault_projects": repo_root / "vault" / "Projects",
        "localai_root": repo_root / "LocalAI",
        "algotrading_root": repo_root / "vault" / "Projects" / "AlgoTrading",
    }
    for name, path in required.items():
        if path.exists():
            checks.append(CheckResult(name=name, status="ok", detail=str(path), severity="info"))
        else:
            checks.append(CheckResult(name=name, status="fail", detail=f"missing: {path}"))
    return checks


def _check_project_rules(repo_root: Path) -> list[CheckResult]:
    projects_root = repo_root / "vault" / "Projects"
    if not projects_root.exists():
        return [CheckResult(name="project_rules_index", status="fail", detail=f"missing: {projects_root}")]

    project_dirs = [p for p in projects_root.iterdir() if p.is_dir()]
    if not project_dirs:
        return [CheckResult(name="project_rules_index", status="fail", detail="no projects in vault/Projects")]

    missing_records: list[str] = []
    for project_dir in sorted(project_dirs, key=lambda p: p.name.lower()):
        required = PROJECT_REQUIRED_BY_NAME.get(project_dir.name, ("00-Rules (Summary).md",))
        for rel in required:
            target = project_dir / rel
            if not target.exists():
                missing_records.append(f"{project_dir.name}: {rel}")

    if missing_records:
        return [
            CheckResult(
                name="project_rules_coverage",
                status="fail",
                detail="; ".join(missing_records),
            )
        ]

    return [
        CheckResult(
            name="project_rules_coverage",
            status="ok",
            detail=f"projects={len(project_dirs)}",
            severity="info",
        )
    ]


def _check_localai_rules(repo_root: Path) -> list[CheckResult]:
    required = (
        repo_root / "LocalAI" / "assistant" / ".trae" / "rules" / "project_rules.md",
        repo_root / "LocalAI" / "assistant" / "README.md",
    )
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        return [
            CheckResult(
                name="localai_rules",
                status="warn",
                detail="; ".join(missing),
                severity="warning",
            )
        ]
    return [
        CheckResult(
            name="localai_rules",
            status="ok",
            detail="LocalAI assistant rules/docs present",
            severity="info",
        )
    ]


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _is_secret_scan_candidate(path: Path) -> bool:
    if path.suffix.lower() not in SECRET_SCAN_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > int(SECRET_SCAN_MAX_BYTES):
            return False
    except OSError:
        return False
    return True


def _iter_reports_scan_files(repo_root: Path) -> list[Path]:
    base = repo_root / "reports"
    if not base.is_dir():
        return []
    out: list[Path] = []
    try:
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if _is_binary_by_extension(p) or not _is_secret_scan_candidate(p):
                continue
            out.append(p)
    except OSError:
        return out
    out.sort(key=lambda x: str(x).lower())
    return out


def _iter_git_tracked_files(repo_root: Path) -> tuple[list[Path], str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(repo_root),
            capture_output=True,
        )
    except FileNotFoundError:
        return [], "git_tool-missing"
    except OSError as e:
        return [], str(e)
    if int(completed.returncode) != 0:
        return [], (completed.stderr or b"").decode("utf-8", errors="replace").strip() or "git_error"
    raw = completed.stdout or b""
    parts = [p for p in raw.split(b"\x00") if p]
    out: list[Path] = []
    for b in parts:
        rel = b.decode("utf-8", errors="replace")
        p = (repo_root / rel).resolve()
        if not p.is_file():
            continue
        if _is_binary_by_extension(p) or not _is_secret_scan_candidate(p):
            continue
        out.append(p)
    out.sort(key=lambda x: str(x).lower())
    return out, ""


def _check_absolute_user_paths(paths: Sequence[Path], repo_root: Path) -> list[CheckResult]:
    findings: list[str] = []
    for path in paths:
        rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        if rel.startswith("tests/"):
            continue
        if path.suffix.lower() not in ABS_PATH_SCAN_EXTENSIONS:
            continue
        text = _read_text_safe(path)
        if not text:
            continue
        if ABSOLUTE_USER_PATH_PATTERN.search(text):
            findings.append(rel)
    if findings:
        return [
            CheckResult(
                name="absolute_user_paths",
                status="warn",
                detail=", ".join(findings[:25]),
                severity="warning",
            )
        ]
    return [
        CheckResult(
            name="absolute_user_paths",
            status="ok",
            detail="no C:\\Users\\ hardcoded paths in scanned files",
            severity="info",
        )
    ]


def _check_secret_patterns(paths: Sequence[Path], repo_root: Path) -> list[CheckResult]:
    checks: list[CheckResult] = []
    errors: list[str] = []
    warnings: list[str] = []
    for path in paths:
        rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        if rel.startswith("tests/"):
            continue
        text = _read_text_safe(path)
        if not text:
            continue
        for name, pattern in SECRET_ERROR_PATTERNS:
            if pattern.search(text):
                errors.append(f"{name}:{rel}")
        for name, pattern in SECRET_WARN_PATTERNS:
            if pattern.search(text):
                warnings.append(f"{name}:{rel}")
    if errors:
        checks.append(
            CheckResult(
                name="secret_scan_errors",
                status="fail",
                detail=", ".join(errors[:25]),
            )
        )
    else:
        checks.append(
            CheckResult(
                name="secret_scan_errors",
                status="ok",
                detail="no high-confidence secrets detected",
                severity="info",
            )
        )
    if warnings:
        checks.append(
            CheckResult(
                name="secret_scan_warnings",
                status="warn",
                detail=", ".join(warnings[:25]),
                severity="warning",
            )
        )
    else:
        checks.append(
            CheckResult(
                name="secret_scan_warnings",
                status="ok",
                detail="no generic secret patterns detected",
                severity="info",
            )
        )
    return checks


def _check_secret_patterns_scoped(paths: Sequence[Path], repo_root: Path, prefix: str) -> list[CheckResult]:
    checks: list[CheckResult] = []
    errors: list[str] = []
    warnings: list[str] = []
    for path in paths:
        rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
        if rel.startswith("tests/"):
            continue
        text = _read_text_safe(path)
        if not text:
            continue
        for name, pattern in SECRET_ERROR_PATTERNS:
            if pattern.search(text):
                errors.append(f"{name}:{rel}")
        for name, pattern in SECRET_WARN_PATTERNS:
            if pattern.search(text):
                warnings.append(f"{name}:{rel}")
    if errors:
        checks.append(
            CheckResult(
                name=f"{prefix}_errors",
                status="fail",
                detail=", ".join(errors[:25]),
            )
        )
    else:
        checks.append(
            CheckResult(
                name=f"{prefix}_errors",
                status="ok",
                detail="no high-confidence secrets detected",
                severity="info",
            )
        )
    if warnings:
        checks.append(
            CheckResult(
                name=f"{prefix}_warnings",
                status="warn",
                detail=", ".join(warnings[:25]),
                severity="warning",
            )
        )
    else:
        checks.append(
            CheckResult(
                name=f"{prefix}_warnings",
                status="ok",
                detail="no generic secret patterns detected",
                severity="info",
            )
        )
    return checks


def _iter_automation_files(repo_root: Path) -> Iterable[Path]:
    for rel in ("scripts", ".github/workflows", "tools"):
        base = repo_root / rel
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if _is_binary_by_extension(p) or _path_contains_excluded_part(p, repo_root):
                continue
            yield p


def _check_risky_commands(repo_root: Path) -> list[CheckResult]:
    findings: list[str] = []
    for path in _iter_automation_files(repo_root):
        text = _read_text_safe(path)
        if not text:
            continue
        for name, pattern in RISKY_PATTERNS:
            if pattern.search(text):
                rel = str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
                findings.append(f"{name}:{rel}")
    if findings:
        return [
            CheckResult(
                name="risky_automation_commands",
                status="fail",
                detail=", ".join(findings[:25]),
            )
        ]
    return [
        CheckResult(
            name="risky_automation_commands",
            status="ok",
            detail="no high-risk destructive/network-disabling commands detected",
            severity="info",
        )
    ]


def _check_ci_guardrails(repo_root: Path) -> list[CheckResult]:
    ci_path = repo_root / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        return [CheckResult(name="ci_guardrails_hook", status="warn", detail="ci.yml missing", severity="warning")]
    text = _read_text_safe(ci_path)
    if "guardrails.py" in text:
        return [
            CheckResult(
                name="ci_guardrails_hook",
                status="ok",
                detail="guardrails integrated in CI",
                severity="info",
            )
        ]
    return [
        CheckResult(
            name="ci_guardrails_hook",
            status="warn",
            detail="ci.yml does not reference guardrails.py",
            severity="warning",
        )
    ]


def run_guardrails(
    repo_root: Path,
    paths: Sequence[Path],
    strict: bool,
    *,
    scan_tracked: bool = False,
    scan_reports: bool = False,
    skip_root_checks: bool = False,
) -> dict:
    checks: list[CheckResult] = []
    if not bool(skip_root_checks):
        checks.extend(_check_core_roots(repo_root))
        checks.extend(_check_project_rules(repo_root))
        checks.extend(_check_localai_rules(repo_root))

    scan_paths = list(paths) if paths else list(_iter_default_scan_files(repo_root))
    checks.extend(_check_absolute_user_paths(scan_paths, repo_root))
    checks.extend(_check_secret_patterns(scan_paths, repo_root))
    if bool(scan_tracked):
        tracked, err = _iter_git_tracked_files(repo_root)
        if err:
            checks.append(CheckResult(name="tracked_files_list", status="warn", detail=err, severity="warning"))
        else:
            checks.extend(_check_secret_patterns_scoped(tracked, repo_root, "secret_scan_tracked"))
    if bool(scan_reports):
        report_paths = _iter_reports_scan_files(repo_root)
        checks.extend(_check_secret_patterns_scoped(report_paths, repo_root, "secret_scan_reports"))
    checks.extend(_check_risky_commands(repo_root))
    checks.extend(_check_ci_guardrails(repo_root))

    errors = [c for c in checks if c.status == "fail" or c.severity == "error" and c.status != "ok"]
    warnings = [c for c in checks if c.status == "warn" or c.severity == "warning" and c.status != "ok"]
    ok = not errors and (not strict or not warnings)
    return {
        "kind": "guardrails_report",
        "repo_root": str(repo_root),
        "strict": strict,
        "ok": ok,
        "errors": [asdict(c) for c in errors],
        "warnings": [asdict(c) for c in warnings],
        "checks": [asdict(c) for c in checks],
        "scanned_files": len(scan_paths),
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrator guardrails checks")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parent),
        help="Path to repository root (default: script directory parent).",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument("--scan-tracked", action="store_true", help="Scan git-tracked files for secret patterns.")
    parser.add_argument("--scan-reports", action="store_true", help="Scan reports/ for secret patterns.")
    parser.add_argument("--skip-root-checks", action="store_true", help="Skip repository root/structure checks.")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--write-report", default="", help="Write JSON report to this file path.")
    parser.add_argument("paths", nargs="*", help="Optional file paths to scan (from pre-commit).")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(list(argv) if argv is not None else sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    input_paths = _resolve_input_paths(repo_root, list(args.paths))
    payload = run_guardrails(
        repo_root=repo_root,
        paths=input_paths,
        strict=bool(args.strict),
        scan_tracked=bool(args.scan_tracked),
        scan_reports=bool(args.scan_reports),
        skip_root_checks=bool(args.skip_root_checks),
    )

    if args.write_report:
        report_path = Path(args.write_report)
        if not report_path.is_absolute():
            report_path = (repo_root / report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"ok={payload['ok']} errors={len(payload['errors'])} warnings={len(payload['warnings'])}")
        print(f"scanned_files={payload['scanned_files']}")
        for row in payload["errors"]:
            print(f"ERROR {row['name']}: {row['detail']}")
        for row in payload["warnings"]:
            print(f"WARN  {row['name']}: {row['detail']}")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
