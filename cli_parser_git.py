from __future__ import annotations

import argparse

from cli_cmd_git import _cmd_git_bootstrap_ignore


def add_git_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    gitp = sub.add_parser("git")
    git_sub = gitp.add_subparsers(dest="git_cmd", required=True)

    gboot = git_sub.add_parser("bootstrap-ignore")
    gboot.add_argument("--roots", nargs="*", default=None)
    gboot.add_argument("--strict-roots", action="store_true")
    gboot.add_argument("--max-depth", type=int, default=3)
    gboot.add_argument("--project", default=None)
    gboot.add_argument("--limit", type=int, default=None)
    gboot.add_argument("--dry-run", action="store_true")
    gboot.add_argument("--json", action="store_true")
    gboot.set_defaults(func=_cmd_git_bootstrap_ignore)
