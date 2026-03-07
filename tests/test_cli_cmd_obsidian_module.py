import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import cli_cmd_obsidian


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "obsidian_bin": "obsidian",
        "vault_root": ".",
        "vault": None,
        "query": "",
        "limit": 50,
        "json": False,
        "reports_dir": ".",
        "report_json": "",
        "backup_dir": "",
        "apply": False,
        "enable_eval": False,
        "profile": "files_count",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class ObsidianCmdModuleTests(unittest.TestCase):
    def test_helpers_basic(self) -> None:
        self.assertEqual(cli_cmd_obsidian._obsidian_kv("a", "b"), "a=b")
        self.assertIsNone(cli_cmd_obsidian._safe_json_loads("not-json"))
        self.assertEqual(cli_cmd_obsidian._normalize_search_results({"results": [{"a": 1}, 2]}), [{"a": 1}])
        self.assertEqual(cli_cmd_obsidian._normalize_tag_counts([{"tag": "#x"}, "bad"]), [{"tag": "#x"}])

    def test_normalize_targets(self) -> None:
        self.assertEqual(cli_cmd_obsidian._normalize_wikilink_target("A|alias#h^b"), "A")
        self.assertEqual(cli_cmd_obsidian._normalize_md_target("<dir/a.md#h?q=1>"), "dir/a.md")
        self.assertEqual(cli_cmd_obsidian._normalize_md_target("https://example.com/x"), "")

    def test_vault_markers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".obsidian").mkdir()
            (root / "KB").mkdir()
            markers = cli_cmd_obsidian._vault_markers(root)
        self.assertIn(".obsidian", markers)
        self.assertIn("KB", markers)

    def test_referenced_targets_and_attachments_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Notes").mkdir(parents=True)
            (root / "Assets").mkdir(parents=True)
            (root / "Notes" / "n.md").write_text(
                "![[Assets/used.png]]\n[doc](Assets/doc.pdf#x)\n",
                encoding="utf-8",
            )
            (root / "Assets" / "used.png").write_bytes(b"x")
            orphan = root / "Assets" / "orphan.png"
            orphan.write_bytes(b"y")
            refs = cli_cmd_obsidian._referenced_targets(root)
            items = cli_cmd_obsidian._attachments_report(root)
        self.assertIn("assets/used.png", refs)
        self.assertEqual([it.rel for it in items], ["Assets/orphan.png"])

    def test_run_obsidian_calls_capture(self) -> None:
        with mock.patch("cli_cmd_obsidian._run_capture", return_value=(0, "ok", "")) as cap:
            code, out, err = cli_cmd_obsidian._run_obsidian("obsidian", ["version"])
        self.assertEqual((code, out, err), (0, "ok", ""))
        self.assertTrue(cap.called)

    def test_cmd_doctor_table_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".obsidian").mkdir()
            args = _ns(vault_root=str(root), json=False)
            out = io.StringIO()
            with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(0, "1.2.3", "warn")):
                with redirect_stdout(out):
                    code = cli_cmd_obsidian._cmd_obsidian_doctor(args)
        self.assertEqual(code, 0)
        printed = out.getvalue()
        self.assertIn("ok", printed)
        self.assertIn("marker", printed)
        self.assertIn("stderr", printed)

    def test_cmd_doctor_json_error_status(self) -> None:
        args = _ns(vault_root=".", json=True)
        out = io.StringIO()
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(3, "", "boom")):
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_doctor(args)
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertEqual(payload.get("status"), "error")
        self.assertFalse(bool(payload.get("obsidian_cli_present")))

    def test_cmd_search_table_mode_error(self) -> None:
        out = io.StringIO()
        args = _ns(query="todo", limit=0, vault="V", json=False)
        payload = json.dumps([{"file": "a.md", "ln": 3, "text": "TODO"}])
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(3, payload, "boom")):
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_search(args)
        self.assertEqual(code, 1)
        text = out.getvalue()
        self.assertIn("a.md", text)
        self.assertIn("stderr", text)

    def test_cmd_search_requires_query(self) -> None:
        args = _ns(query="")
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_obsidian._cmd_obsidian_search(args)
        self.assertEqual(code, 2)
        self.assertIn("query required", err.getvalue())

    def test_cmd_tags_counts_table_mode(self) -> None:
        out = io.StringIO()
        payload = json.dumps([{"name": "#tag", "n": 5}])
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(0, payload, "warn")):
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_tags_counts(_ns(json=False))
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("#tag", text)
        self.assertIn("stderr", text)

    def test_cmd_attachments_report_table_mode(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            assets = vault / "Assets"
            assets.mkdir(parents=True)
            (assets / "x.png").write_bytes(b"x")
            reports = Path(td) / "reports"
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_attachments_report(
                    _ns(vault_root=str(vault), reports_dir=str(reports), json=False)
                )
        self.assertEqual(code, 0)
        self.assertIn("report_json", out.getvalue())

    def test_cmd_attachments_delete_validates_inputs(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = cli_cmd_obsidian._cmd_obsidian_attachments_delete(_ns(apply=False))
        self.assertEqual(code, 2)
        self.assertIn("apply required", err.getvalue())

        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "report.json"
            report.write_text("{}", encoding="utf-8")
            args = _ns(apply=True, vault_root=td, report_json=str(report), backup_dir=str(Path(td) / "b"))
            err2 = io.StringIO()
            with redirect_stderr(err2):
                code2 = cli_cmd_obsidian._cmd_obsidian_attachments_delete(args)
        self.assertEqual(code2, 2)
        self.assertIn("candidates missing", err2.getvalue())

    def test_cmd_attachments_delete_handles_outside_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            vault.mkdir()
            report = Path(td) / "report.json"
            report.write_text(
                json.dumps({"candidates": [{"rel": "../outside.png"}, {"rel": "ghost.png"}]}),
                encoding="utf-8",
            )
            out = io.StringIO()
            args = _ns(
                apply=True,
                json=True,
                vault_root=str(vault),
                report_json=str(report),
                backup_dir=str(Path(td) / "backup"),
            )
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_attachments_delete(args)
        self.assertEqual(code, 1)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(r.get("error") == "outside_vault" for r in rows))
        self.assertTrue(any(r.get("status") == "missing" for r in rows))

    def test_cmd_attachments_delete_bad_report_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            report = Path(td) / "bad.json"
            report.write_text("{broken", encoding="utf-8")
            err = io.StringIO()
            args = _ns(apply=True, vault_root=td, report_json=str(report), backup_dir=str(Path(td) / "backup"), json=True)
            with redirect_stderr(err):
                code = cli_cmd_obsidian._cmd_obsidian_attachments_delete(args)
        self.assertEqual(code, 2)
        self.assertIn("bad report_json", err.getvalue())

    def test_cmd_attachments_delete_copy_failure_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            vault.mkdir()
            src = vault / "Assets" / "a.png"
            src.parent.mkdir(parents=True, exist_ok=True)
            src.write_bytes(b"abc")
            report = Path(td) / "report.json"
            report.write_text(json.dumps({"candidates": [{"rel": "Assets/a.png"}]}), encoding="utf-8")
            out = io.StringIO()
            args = _ns(
                apply=True,
                json=True,
                vault_root=str(vault),
                report_json=str(report),
                backup_dir=str(Path(td) / "backup"),
            )
            with (
                mock.patch("cli_cmd_obsidian.shutil.copy2", side_effect=OSError("disk full")),
                redirect_stdout(out),
            ):
                code = cli_cmd_obsidian._cmd_obsidian_attachments_delete(args)
        self.assertEqual(code, 1)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(r.get("kind") == "obsidian_attachment_delete" and r.get("ok") is False for r in rows))
        summary = next(r for r in rows if r.get("kind") == "obsidian_attachments_delete_summary")
        self.assertEqual(int(summary.get("failed", 0)), 1)

    def test_cmd_eval_profile_missing_and_enabled_success(self) -> None:
        bad_args = _ns(enable_eval=True, profile="missing", json=False)
        err = io.StringIO()
        with redirect_stderr(err):
            bad = cli_cmd_obsidian._cmd_obsidian_eval(bad_args)
        self.assertEqual(bad, 2)
        self.assertIn("profile not found", err.getvalue())

        out = io.StringIO()
        ok_args = _ns(enable_eval=True, profile="files_count", json=False, vault="Main")
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(0, "42\n", "")):
            with redirect_stdout(out):
                ok = cli_cmd_obsidian._cmd_obsidian_eval(ok_args)
        self.assertEqual(ok, 0)
        self.assertIn("result", out.getvalue())

    def test_cmd_eval_enabled_runtime_error_table(self) -> None:
        out = io.StringIO()
        args = _ns(enable_eval=True, profile="files_count", json=False, vault="Main")
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(9, "", "eval failed")):
            with redirect_stdout(out):
                code = cli_cmd_obsidian._cmd_obsidian_eval(args)
        self.assertEqual(code, 1)
        text = out.getvalue()
        self.assertIn("error", text)
        self.assertIn("stderr", text)
