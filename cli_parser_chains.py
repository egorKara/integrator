from __future__ import annotations

import argparse

from cli_cmd_misc import _cmd_chains_list, _cmd_chains_plan


def add_chains_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    chains = sub.add_parser("chains")
    chains_sub = chains.add_subparsers(dest="chains_cmd", required=True)

    clist = chains_sub.add_parser("list")
    clist.add_argument("--chains", default=None)
    clist.add_argument("--json", action="store_true")
    clist.set_defaults(func=_cmd_chains_list)

    cplan = chains_sub.add_parser("plan")
    cplan.add_argument("name")
    cplan.add_argument("--chains", default=None)
    cplan.add_argument("--json", action="store_true")
    cplan.set_defaults(func=_cmd_chains_plan)
