from __future__ import annotations

import argparse

from cli_cmd_projects import _cmd_projects_info, _cmd_projects_list


def add_projects_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    projects = sub.add_parser("projects")
    projects_sub = projects.add_subparsers(dest="projects_cmd", required=True)

    plist = projects_sub.add_parser("list")
    plist.add_argument("--roots", nargs="*", default=None)
    plist.add_argument("--strict-roots", action="store_true")
    plist.add_argument("--max-depth", type=int, default=3)
    plist.add_argument("--project", default=None)
    plist.add_argument("--limit", type=int, default=None)
    plist.add_argument("--json", action="store_true")
    plist.set_defaults(func=_cmd_projects_list)

    pscan = projects_sub.add_parser("scan")
    pscan.add_argument("--roots", nargs="*", default=None)
    pscan.add_argument("--strict-roots", action="store_true")
    pscan.add_argument("--max-depth", type=int, default=3)
    pscan.add_argument("--project", default=None)
    pscan.add_argument("--limit", type=int, default=None)
    pscan.add_argument("--json", action="store_true")
    pscan.set_defaults(func=_cmd_projects_list)

    pinfo = projects_sub.add_parser("info")
    pinfo.add_argument("--roots", nargs="*", default=None)
    pinfo.add_argument("--strict-roots", action="store_true")
    pinfo.add_argument("--max-depth", type=int, default=3)
    pinfo.add_argument("--project", default=None)
    pinfo.add_argument("--limit", type=int, default=None)
    pinfo.add_argument("--json", action="store_true")
    pinfo.set_defaults(func=_cmd_projects_info)
