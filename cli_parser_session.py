from __future__ import annotations

import argparse

from cli_workflow import _cmd_workflow_session_close, _cmd_zapovednik_start


def add_session_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    session = sub.add_parser("session")
    session_sub = session.add_subparsers(dest="session_cmd", required=True)

    session_open = session_sub.add_parser("open")
    session_open.add_argument("--json", action="store_true")
    session_open.set_defaults(func=_cmd_zapovednik_start)

    session_close = session_sub.add_parser("close")
    session_close.add_argument("--reports-dir", default="reports")
    session_close.add_argument("--date", default=None)
    session_close.add_argument("--owner", default="AI Agent (Integrator CLI Engineer)")
    session_close.add_argument("--task-id", default="B16")
    session_close.add_argument("--dry-run", action="store_true")
    session_close.add_argument("--skip-quality", action="store_true")
    session_close.add_argument("--json", action="store_true")
    session_close.set_defaults(func=_cmd_workflow_session_close)
