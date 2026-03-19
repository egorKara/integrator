from __future__ import annotations

import argparse
from typing import Sequence

from agent_memory_client import memory_write_file
from cli_env import default_roots
from cli_runtime import build_cli_parser, default_prog, run_cli
from services_preflight import wait_ready
from utils import _load_global_gitignore, _run_capture

__all__ = [
    "default_roots",
    "memory_write_file",
    "run",
    "wait_ready",
    "_load_global_gitignore",
    "_run_capture",
]


def _default_prog(argv0: str) -> str:
    return default_prog(argv0)


def _build_parser(prog: str) -> argparse.ArgumentParser:
    return build_cli_parser(prog=prog)


def _run_cli(argv: Sequence[str]) -> int:
    return run_cli(argv)


def run(argv: Sequence[str]) -> int:
    return _run_cli(argv)
