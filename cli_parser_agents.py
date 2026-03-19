from __future__ import annotations

import argparse
import os

from cli_cmd_agents import _cmd_agents_list, _cmd_agents_status


def _default_jobs() -> int:
    return min(16, (os.cpu_count() or 4) * 2)


def add_agents_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    agents = sub.add_parser("agents")
    agents_sub = agents.add_subparsers(dest="agents_cmd", required=True)

    alist = agents_sub.add_parser("list")
    alist.add_argument("--roots", nargs="*", default=None)
    alist.add_argument("--strict-roots", action="store_true")
    alist.add_argument("--max-depth", type=int, default=4)
    alist.add_argument("--project", default=None)
    alist.add_argument("--limit", type=int, default=None)
    alist.add_argument("--json", action="store_true")
    alist.set_defaults(func=_cmd_agents_list)

    astatus = agents_sub.add_parser("status")
    astatus.add_argument("--roots", nargs="*", default=None)
    astatus.add_argument("--strict-roots", action="store_true")
    astatus.add_argument("--max-depth", type=int, default=4)
    astatus.add_argument("--jobs", type=int, default=_default_jobs())
    astatus.add_argument("--project", default=None)
    astatus.add_argument("--limit", type=int, default=None)
    astatus.add_argument("--json", action="store_true")
    astatus.add_argument("--only-problems", action="store_true")
    astatus.add_argument("--fix-hints", action="store_true")
    astatus.add_argument("--explain", action="store_true")
    astatus.set_defaults(func=_cmd_agents_status)
