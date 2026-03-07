from __future__ import annotations

import argparse

from cli_cmd_misc import _cmd_diagnostics, _cmd_doctor, _cmd_preflight
from cli_env import default_localai_assistant_root
from services_preflight import default_lm_studio_base_url


def add_health_parsers(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=_cmd_doctor)

    diag = sub.add_parser("diagnostics")
    diag.add_argument("--roots", nargs="*", default=None)
    diag.add_argument("--only-problems", action="store_true")
    diag.add_argument("--json", action="store_true")
    diag.set_defaults(func=_cmd_diagnostics)

    preflight = sub.add_parser("preflight")
    preflight.add_argument("--rag-cwd", default=str(default_localai_assistant_root()))
    preflight.add_argument("--rag-base-url", default="http://127.0.0.1:8011")
    preflight.add_argument("--lm-base-url", default=default_lm_studio_base_url())
    preflight.add_argument("--check-only", action="store_true")
    preflight.add_argument("--json", action="store_true")
    preflight.set_defaults(func=_cmd_preflight)
