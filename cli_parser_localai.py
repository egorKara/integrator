from __future__ import annotations

import argparse

from cli_cmd_localai import _cmd_localai_assistant, _cmd_localai_list
from cli_env import default_localai_root


def add_localai_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    localai = sub.add_parser("localai")
    localai_sub = localai.add_subparsers(dest="localai_cmd", required=True)

    llist = localai_sub.add_parser("list")
    llist.add_argument("--root", default=str(default_localai_root()))
    llist.add_argument("--max-depth", type=int, default=3)
    llist.add_argument("--project", default=None)
    llist.add_argument("--limit", type=int, default=None)
    llist.set_defaults(func=_cmd_localai_list)

    assistant = localai_sub.add_parser("assistant")
    assistant.add_argument(
        "recipe",
        choices=[
            "mcp",
            "rag",
            "reindex",
            "smoke",
            "memory-write",
            "memory-search",
            "memory-recent",
            "memory-retrieve",
            "memory-stats",
            "memory-feedback",
            "task-add",
            "tasks-pending",
            "task-close",
        ],
    )
    assistant.add_argument("--cwd", default=None)
    assistant.add_argument("--daemon", action="store_true")
    assistant.add_argument("--base-url", default="http://127.0.0.1:8011")
    assistant.add_argument("--gateway-json", default=None)
    assistant.add_argument("--auth-token", default=None)
    assistant.add_argument("--content-file", default=None)
    assistant.add_argument("--summary", default=None)
    assistant.add_argument("--kind", default="event")
    assistant.add_argument("--filter-kind", default=None)
    assistant.add_argument("--tags", nargs="*", default=[])
    assistant.add_argument("--source", default=None)
    assistant.add_argument("--author", default=None)
    assistant.add_argument("--module", default="integrator")
    assistant.add_argument("--filter-module", default=None)
    assistant.add_argument("--chunk-size", type=int, default=20000)
    assistant.add_argument("--q", default=None)
    assistant.add_argument("--limit", type=int, default=10)
    assistant.add_argument("--min-importance", type=float, default=None)
    assistant.add_argument("--min-trust", type=float, default=None)
    assistant.add_argument("--max-age-sec", type=int, default=None)
    assistant.add_argument("--include-quarantined", action="store_true")
    assistant.add_argument("--include-deleted", action="store_true")
    assistant.add_argument("--id", type=int, default=None)
    assistant.add_argument("--rating", type=int, default=None)
    assistant.add_argument("--notes", default=None)
    assistant.add_argument("--title", default=None)
    assistant.add_argument("--prio", default="p2")
    assistant.add_argument("--owner", default=None)
    assistant.add_argument("--next-step", default=None)
    assistant.add_argument("--json", action="store_true")
    assistant.set_defaults(func=_cmd_localai_assistant)
