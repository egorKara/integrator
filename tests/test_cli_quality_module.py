from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cli_quality


class TestCliQuality(unittest.TestCase):
    def test_tool_version_strips_output(self) -> None:
        with patch.object(cli_quality, "_run_capture", return_value=(0, "x \n", "y \n")):
            r = cli_quality._tool_version(["x"], Path("."))
        self.assertEqual(r["code"], 0)
        self.assertEqual(r["out"], "x")
        self.assertEqual(r["err"], "y")

    def test_coverage_gate_run_failure(self) -> None:
        calls: list[list[str]] = []

        def fake_gate(cmd: list[str], cwd: Path):
            calls.append(cmd)
            return {"code": 2, "out": "no", "err": "bad"}

        with patch.object(cli_quality, "_gate", side_effect=fake_gate):
            r = cli_quality._coverage_gate("python", Path("."), fail_under=80)

        self.assertEqual(r["code"], 2)
        self.assertEqual(r["stage"], "run")
        self.assertTrue(calls)

    def test_coverage_gate_xml_failure_propagates(self) -> None:
        seq = [
            {"code": 0, "out": "ok", "err": ""},
            {"code": 0, "out": "report", "err": ""},
            {"code": 3, "out": "xml", "err": "xmlfail"},
        ]

        def fake_gate(cmd: list[str], cwd: Path):
            return seq.pop(0)

        with tempfile.TemporaryDirectory() as td:
            cwd = Path(td)
            with patch.object(cli_quality, "_gate", side_effect=fake_gate):
                r = cli_quality._coverage_gate("python", cwd, fail_under=80)

        self.assertEqual(r["stage"], "report")
        self.assertEqual(r["code"], 3)
        self.assertEqual(r["xml_code"], 3)

    def test_cmd_quality_summary_writes_report_without_running_gates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "q.json"
                args = argparse.Namespace(json=True, no_run=True, fail_under=80, write_report=str(out_path))

                def fake_run_capture(cmd: list[str], cwd: Path):
                    return 0, "ok", ""

                with patch.object(cli_quality, "_run_capture", side_effect=fake_run_capture):
                    code = cli_quality._cmd_quality_summary(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "quality_summary")
            self.assertEqual(payload["gates"], {})

    def test_cmd_quality_github_snapshot_invalid_repo(self) -> None:
        args = argparse.Namespace(repo="bad-slug", state="open", write_report=None, json=True)
        code = cli_quality._cmd_quality_github_snapshot(args)
        self.assertEqual(code, 2)

    def test_cmd_quality_github_snapshot_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            prev = os.getcwd()
            os.chdir(td)
            try:
                out_path = Path(td) / "reports" / "snap.json"
                args = argparse.Namespace(repo="egorKara/integrator", state="open", write_report=str(out_path), json=True)

                def fake_list(url: str, token: str | None):
                    if "/issues?" in url:
                        return {
                            "ok": True,
                            "status": 200,
                            "error": "",
                            "items": [
                                {"number": 1, "title": "Issue", "state": "open", "updated_at": "2026-01-01", "html_url": "u1"},
                                {
                                    "number": 2,
                                    "title": "PR-like in issues",
                                    "state": "open",
                                    "updated_at": "2026-01-01",
                                    "html_url": "u2",
                                    "pull_request": {"url": "x"},
                                },
                            ],
                        }
                    return {
                        "ok": True,
                        "status": 200,
                        "error": "",
                        "items": [
                            {
                                "number": 3,
                                "title": "PR",
                                "state": "open",
                                "updated_at": "2026-01-02",
                                "html_url": "u3",
                                "draft": False,
                            }
                        ],
                    }

                with (
                    patch.object(cli_quality, "_github_list_all", side_effect=fake_list),
                    patch.object(cli_quality, "load_github_token", return_value="t"),
                ):
                    code = cli_quality._cmd_quality_github_snapshot(args)
            finally:
                os.chdir(prev)

            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["kind"], "github_snapshot")
            self.assertEqual(payload["issues_open_count"], 1)
            self.assertEqual(payload["pulls_open_count"], 1)

    def test_github_list_all_handles_pagination(self) -> None:
        class Resp:
            def __init__(self, ok: bool, status: int, json_payload):
                self.ok = ok
                self.status = status
                self.json = json_payload
                self.error = None

        seq = [
            Resp(True, 200, [{"n": 1}] * 100),
            Resp(True, 200, [{"n": 2}]),
        ]
        with patch.object(cli_quality, "github_api_request", side_effect=lambda *args, **kwargs: seq.pop(0)):
            result = cli_quality._github_list_all("https://api.github.com/repos/a/b/issues?state=open", "t")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["items"]), 101)

    def test_github_list_all_handles_error(self) -> None:
        class Resp:
            ok = False
            status = 403
            json = None
            error = "denied"

        with patch.object(cli_quality, "github_api_request", return_value=Resp()):
            result = cli_quality._github_list_all("https://api.github.com/repos/a/b/issues?state=open", "t")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 403)

    def test_cmd_quality_github_snapshot_returns_error_on_api_failure(self) -> None:
        args = argparse.Namespace(repo="egorKara/integrator", state="open", write_report=None, json=True)
        with patch.object(cli_quality, "_github_list_all", return_value={"ok": False, "status": 500, "error": "e", "items": []}):
            code = cli_quality._cmd_quality_github_snapshot(args)
        self.assertEqual(code, 1)
