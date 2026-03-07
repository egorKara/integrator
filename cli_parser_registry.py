from __future__ import annotations

import argparse

from cli_cmd_misc import _cmd_registry_list


def add_registry_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    registry = sub.add_parser("registry")
    registry_sub = registry.add_subparsers(dest="registry_cmd", required=True)

    rlist = registry_sub.add_parser("list")
    rlist.add_argument("--registry", default=None)
    rlist.add_argument("--json", action="store_true")
    rlist.set_defaults(func=_cmd_registry_list)
