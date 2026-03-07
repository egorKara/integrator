from __future__ import annotations

import argparse

from cli_cmd_hygiene import _cmd_hygiene
from cli_cmd_misc import _cmd_exec, _cmd_rg


def add_tools_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    rgp = sub.add_parser("rg")
    rgp.add_argument("--cwd", default=".")
    rgp.add_argument("--no-defaults", action="store_true")
    rgp.add_argument("args", nargs=argparse.REMAINDER)
    rgp.set_defaults(func=_cmd_rg)

    execp = sub.add_parser("exec")
    execp.add_argument("--cwd", required=True)
    execp.add_argument("command", nargs=argparse.REMAINDER)
    execp.set_defaults(func=_cmd_exec)

    hygiene = sub.add_parser("hygiene")
    hygiene.add_argument("--roots", nargs="*", default=None)
    hygiene.add_argument("--strict-roots", action="store_true")
    hygiene.add_argument("--max-depth", type=int, default=3)
    hygiene.add_argument("--project", default=None)
    hygiene.add_argument("--limit", type=int, default=None)
    hygiene.add_argument("--dry-run", action="store_true")
    hygiene.add_argument("--apply", action="store_true")
    hygiene.add_argument("--json", action="store_true")
    hygiene.set_defaults(func=_cmd_hygiene)
