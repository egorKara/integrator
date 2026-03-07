from __future__ import annotations

import argparse
import os

from cli_cmd_git import _cmd_remotes, _cmd_report, _cmd_status
from cli_cmd_run import _cmd_run


def _default_jobs() -> int:
    return min(16, (os.cpu_count() or 4) * 2)


def add_batch_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    status = sub.add_parser("status")
    status.add_argument("--roots", nargs="*", default=None)
    status.add_argument("--strict-roots", action="store_true")
    status.add_argument("--max-depth", type=int, default=3)
    status.add_argument("--jobs", type=int, default=_default_jobs())
    status.add_argument("--project", default=None)
    status.add_argument("--limit", type=int, default=None)
    status.add_argument("--only-dirty", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=_cmd_status)

    remotes = sub.add_parser("remotes")
    remotes.add_argument("--roots", nargs="*", default=None)
    remotes.add_argument("--strict-roots", action="store_true")
    remotes.add_argument("--max-depth", type=int, default=3)
    remotes.add_argument("--jobs", type=int, default=_default_jobs())
    remotes.add_argument("--project", default=None)
    remotes.add_argument("--limit", type=int, default=None)
    remotes.add_argument("--only-github", action="store_true")
    remotes.add_argument("--json", action="store_true")
    remotes.set_defaults(func=_cmd_remotes)

    runp = sub.add_parser("run")
    runp.add_argument("preset", choices=["lint", "test", "build"])
    runp.add_argument("--roots", nargs="*", default=None)
    runp.add_argument("--strict-roots", action="store_true")
    runp.add_argument("--max-depth", type=int, default=3)
    runp.add_argument("--project", default=None)
    runp.add_argument("--cwd", default=None)
    runp.add_argument("--continue-on-error", action="store_true")
    runp.add_argument("--dry-run", action="store_true")
    runp.add_argument("--json", action="store_true")
    runp.add_argument("--json-strict", action="store_true")
    runp.add_argument("--quiet", action="store_true")
    runp.add_argument("--quiet-tools", action="store_true")
    runp.add_argument("--require-clean", action="store_true")
    runp.set_defaults(func=_cmd_run)

    report = sub.add_parser("report")
    report.add_argument("--roots", nargs="*", default=None)
    report.add_argument("--strict-roots", action="store_true")
    report.add_argument("--max-depth", type=int, default=3)
    report.add_argument("--jobs", type=int, default=_default_jobs())
    report.add_argument("--project", default=None)
    report.add_argument("--limit", type=int, default=None)
    report.add_argument("--format", choices=["tsv", "jsonl", "md"], default="tsv")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=_cmd_report)
