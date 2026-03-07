from __future__ import annotations

import argparse

from cli_cmd_algotrading import add_algotrading_parsers
from cli_cmd_obsidian import add_obsidian_parsers
from cli_incidents import add_incidents_parsers
from cli_parser_agents import add_agents_parsers
from cli_parser_batch import add_batch_parsers
from cli_parser_chains import add_chains_parsers
from cli_parser_git import add_git_parsers
from cli_parser_health import add_health_parsers
from cli_parser_localai import add_localai_parsers
from cli_parser_projects import add_projects_parsers
from cli_parser_registry import add_registry_parsers
from cli_parser_session import add_session_parsers
from cli_parser_tools import add_tools_parsers
from cli_perf import add_perf_parsers
from cli_quality import add_quality_parsers
from cli_workflow import add_workflow_parsers


def _register_primary_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    add_health_parsers(sub)
    add_projects_parsers(sub)
    add_batch_parsers(sub)
    add_agents_parsers(sub)
    add_localai_parsers(sub)
    add_chains_parsers(sub)
    add_registry_parsers(sub)
    add_git_parsers(sub)
    add_tools_parsers(sub)
    add_session_parsers(sub)


def _register_extension_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    add_quality_parsers(sub)
    add_workflow_parsers(sub)
    add_perf_parsers(sub)
    add_incidents_parsers(sub)
    add_algotrading_parsers(sub)
    add_obsidian_parsers(sub)


def build_parser(prog: str) -> argparse.ArgumentParser:
    from version import __version__

    parser = argparse.ArgumentParser(prog=prog)
    parser.add_argument("-v", "--version", action="version", version=__version__)

    sub = parser.add_subparsers(dest="cmd", required=True)

    _register_primary_parsers(sub)
    _register_extension_parsers(sub)

    return parser
