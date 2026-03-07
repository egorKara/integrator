from __future__ import annotations

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import cli_cmd_misc
from services_preflight import ServiceCheck


class TestCliCmdMiscModule(unittest.TestCase):
    def test_cmd_diagnostics_json_and_only_problems(self) -> None:
        args = argparse.Namespace(roots=None, only_problems=True, json=True)
        rows = [
            {"kind": "root", "name": "a", "status": "ok", "path": "x"},
            {"kind": "root", "name": "b", "status": "missing", "path": "y"},
        ]
        printed: list[dict[str, object]] = []
        with (
            mock.patch.object(cli_cmd_misc, "_diagnostics_rows", return_value=rows),
            mock.patch.object(cli_cmd_misc, "_print_json", side_effect=lambda r: printed.append(dict(r))),
        ):
            code = cli_cmd_misc._cmd_diagnostics(args)
        self.assertEqual(code, 1)
        self.assertEqual(len(printed), 1)
        self.assertEqual(printed[0]["name"], "b")

    def test_cmd_preflight_check_only_tab_output(self) -> None:
        args = argparse.Namespace(
            check_only=True,
            rag_cwd=".",
            rag_base_url="http://127.0.0.1:8011",
            lm_base_url="http://127.0.0.1:1234",
            json=False,
        )
        waits = [
            ServiceCheck(name="", url="http://127.0.0.1:8011/health", ok=False, status=503, error="rag_down"),
            ServiceCheck(name="", url="http://127.0.0.1:1234/v1/models", ok=True, status=200, error=""),
        ]
        tabs: list[list[object]] = []
        with (
            mock.patch("cli.wait_ready", side_effect=waits),
            mock.patch.object(cli_cmd_misc, "_print_tab", side_effect=lambda row: tabs.append(list(row))),
        ):
            code = cli_cmd_misc._cmd_preflight(args)
        self.assertEqual(code, 1)
        self.assertEqual(len(tabs), 2)
        self.assertEqual(str(tabs[0][0]), "rag")
        rag_ok_cell = tabs[0][1]
        self.assertIsInstance(rag_ok_cell, int)
        self.assertEqual(rag_ok_cell, 0)
        self.assertEqual(str(tabs[1][0]), "lm_studio")
        lm_ok_cell = tabs[1][1]
        self.assertIsInstance(lm_ok_cell, int)
        self.assertEqual(lm_ok_cell, 1)

    def test_cmd_preflight_starts_services_when_not_check_only(self) -> None:
        args = argparse.Namespace(
            check_only=False,
            rag_cwd=".",
            rag_base_url="http://127.0.0.1:8011",
            lm_base_url="http://127.0.0.1:1234",
            json=True,
        )
        waits = [
            ServiceCheck(name="", url="rag", ok=False, status=503, error="x"),
            ServiceCheck(name="", url="rag", ok=True, status=200, error=""),
            ServiceCheck(name="", url="lm", ok=False, status=503, error="x"),
            ServiceCheck(name="", url="lm", ok=True, status=200, error=""),
        ]
        payloads: list[dict[str, object]] = []
        with (
            mock.patch("cli.wait_ready", side_effect=waits),
            mock.patch.object(cli_cmd_misc, "_resolve_python_command", return_value="python"),
            mock.patch.object(cli_cmd_misc, "try_start_rag", return_value=(True, "")) as rag_start,
            mock.patch.object(cli_cmd_misc, "try_start_lm_studio", return_value=(True, "")) as lm_start,
            mock.patch.object(cli_cmd_misc, "_print_json", side_effect=lambda row: payloads.append(dict(row))),
        ):
            code = cli_cmd_misc._cmd_preflight(args)
        self.assertEqual(code, 0)
        self.assertTrue(rag_start.called)
        self.assertTrue(lm_start.called)
        self.assertEqual(payloads[0]["kind"], "preflight")

    def test_cmd_exec_requires_command(self) -> None:
        args = argparse.Namespace(command=[], cwd=".")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_misc._cmd_exec(args)
        self.assertEqual(code, 2)
        self.assertIn("command is required", err.getvalue())

    def test_resolve_rg_exe_prefers_env_then_localappdata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env_rg = root / "env" / "rg.exe"
            env_rg.parent.mkdir(parents=True, exist_ok=True)
            env_rg.write_text("", encoding="utf-8")
            with mock.patch.dict(cli_cmd_misc.os.environ, {"RG_PATH": str(env_rg)}, clear=True):
                self.assertEqual(cli_cmd_misc._resolve_rg_exe(), str(env_rg))

        with tempfile.TemporaryDirectory() as td:
            local = Path(td)
            embedded = (
                local
                / "Programs"
                / "Trae"
                / "resources"
                / "app"
                / "node_modules"
                / "@vscode"
                / "ripgrep"
                / "bin"
                / "rg.exe"
            )
            embedded.parent.mkdir(parents=True, exist_ok=True)
            embedded.write_text("", encoding="utf-8")
            with (
                mock.patch.dict(cli_cmd_misc.os.environ, {"RG_PATH": "", "LOCALAPPDATA": str(local)}, clear=True),
                mock.patch.object(cli_cmd_misc.shutil, "which", return_value=None),
            ):
                self.assertEqual(cli_cmd_misc._resolve_rg_exe(), str(embedded))

    def test_cmd_rg_without_binary_and_default_help(self) -> None:
        args_missing = argparse.Namespace(cwd=".", args=[], no_defaults=False)
        err = io.StringIO()
        with (
            mock.patch.object(cli_cmd_misc, "_resolve_rg_exe", return_value=None),
            redirect_stderr(err),
        ):
            code = cli_cmd_misc._cmd_rg(args_missing)
        self.assertEqual(code, 127)
        self.assertIn("rg not found", err.getvalue())

        args_help = argparse.Namespace(cwd=".", args=[], no_defaults=True)
        captured: list[object] = []

        def fake_run(cmd: list[str], cwd: Path) -> int:
            captured.extend([cmd, cwd])
            return 0

        with (
            mock.patch.object(cli_cmd_misc, "_resolve_rg_exe", return_value="rg"),
            mock.patch.object(cli_cmd_misc, "_run_command", side_effect=fake_run),
        ):
            ok_code = cli_cmd_misc._cmd_rg(args_help)
        self.assertEqual(ok_code, 0)
        cmd = captured[0]
        self.assertIsInstance(cmd, list)
        assert isinstance(cmd, list)
        self.assertIn("--help", cmd)

    def test_cmd_registry_and_chains_handle_non_list_fields(self) -> None:
        reg_args = argparse.Namespace(registry=None, json=False)
        with (
            mock.patch.object(cli_cmd_misc, "load_registry", return_value=[]),
            mock.patch.object(
                cli_cmd_misc,
                "registry_rows",
                return_value=[{"name": "n", "root": "r", "status": "ok", "priority": "p2", "entrypoint": "", "tags": "x"}],
            ),
            mock.patch.object(cli_cmd_misc, "_print_tab") as tab_mock,
        ):
            self.assertEqual(cli_cmd_misc._cmd_registry_list(reg_args), 0)
        self.assertTrue(tab_mock.called)

        chain_args = argparse.Namespace(chains=None, json=False)
        with (
            mock.patch.object(cli_cmd_misc, "load_chains", return_value=[]),
            mock.patch.object(
                cli_cmd_misc,
                "chain_rows",
                return_value=[{"name": "c", "description": "d", "steps": "bad"}],
            ),
            mock.patch.object(cli_cmd_misc, "_print_tab") as chain_tab,
        ):
            self.assertEqual(cli_cmd_misc._cmd_chains_list(chain_args), 0)
        self.assertTrue(chain_tab.called)

    def test_cmd_chains_plan_not_found_and_found(self) -> None:
        args_missing = argparse.Namespace(chains=None, name="x", json=False)
        err = io.StringIO()
        with (
            mock.patch.object(cli_cmd_misc, "load_chains", return_value=[]),
            redirect_stderr(err),
        ):
            code_missing = cli_cmd_misc._cmd_chains_plan(args_missing)
        self.assertEqual(code_missing, 2)
        self.assertIn("chain not found", err.getvalue())

        chain = SimpleNamespace(name="demo", description="desc", steps=[("echo", "1"), ("echo", "2")])
        args_ok = argparse.Namespace(chains=None, name="demo", json=False)
        out = io.StringIO()
        with (
            mock.patch.object(cli_cmd_misc, "load_chains", return_value=[chain]),
            mock.patch.object(cli_cmd_misc, "_print_tab"),
            redirect_stdout(out),
        ):
            code_ok = cli_cmd_misc._cmd_chains_plan(args_ok)
        self.assertEqual(code_ok, 0)
        self.assertIn("echo 1", out.getvalue())

