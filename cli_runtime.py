from __future__ import annotations

import argparse
from typing import Sequence

from cli_parser_core import build_parser


def default_prog(argv0: str) -> str:
    return "integrator"


def build_cli_parser(prog: str) -> argparse.ArgumentParser:
    return build_parser(prog)


def _argv_list(argv: Sequence[str]) -> list[str]:
    return list(argv)


def _argv_prog(argv: list[str]) -> str:
    return argv[0] if argv else ""


def _argv_args(argv: list[str]) -> list[str]:
    return argv[1:]


def run_cli(argv: Sequence[str]) -> int:
    argv_list = _argv_list(argv)
    prog = default_prog(_argv_prog(argv_list))
    parser = build_cli_parser(prog=prog)
    args = parser.parse_args(_argv_args(argv_list))
    return int(args.func(args))
