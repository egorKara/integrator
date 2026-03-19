from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence, TypedDict

NOISE_PATTERNS = ("cwd not found:", "recipe target not found:")


class GuardPayload(TypedDict):
    kind: str
    status: str
    log_path: str
    errors: list[str]
    noise_matches: list[str]


def check(log_path: Path) -> GuardPayload:
    if not log_path.exists():
        return {
            "kind": "negative_tests_stderr_guard",
            "status": "fail",
            "log_path": str(log_path),
            "errors": ["unittest_log_missing"],
            "noise_matches": [],
        }
    text = log_path.read_text(encoding="utf-8", errors="replace")
    matches = [pattern for pattern in NOISE_PATTERNS if pattern in text]
    status = "pass" if not matches else "fail"
    return {
        "kind": "negative_tests_stderr_guard",
        "status": status,
        "log_path": str(log_path),
        "errors": [],
        "noise_matches": matches,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guard: negative CLI tests should capture stderr")
    parser.add_argument("--log-path", default="reports/unittest.log")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload: GuardPayload = check(Path(args.log_path).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"log_path={payload['log_path']}")
        print(f"status={payload['status']}")
        for item in payload["noise_matches"]:
            print(f"NOISE {item}")
        for item in payload["errors"]:
            print(f"ERROR {item}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
