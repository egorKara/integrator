import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app import run
from tests.io_capture import capture_stdio


class ObsidianCliTests(unittest.TestCase):
    def test_obsidian_doctor_missing_cli(self) -> None:
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(127, "", "tool not found: obsidian")):
            with capture_stdio() as (out, _err):
                code = run(["integrator", "obsidian", "doctor", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertFalse(payload["obsidian_cli_present"])
        self.assertEqual(payload["status"], "missing")

    def test_obsidian_search_jsonl(self) -> None:
        fake = json.dumps({"results": [{"path": "a.md", "line": 1, "match": "TODO"}]})
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(0, fake, "")):
            with capture_stdio() as (out, _err):
                code = run(["integrator", "obsidian", "search", "--query", "TODO", "--json"])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(r.get("kind") == "obsidian_search_result" for r in rows))
        self.assertTrue(any(r.get("kind") == "obsidian_search_summary" for r in rows))

    def test_obsidian_tags_counts_jsonl(self) -> None:
        fake = json.dumps({"results": [{"tag": "#t", "count": 2}]})
        with mock.patch("cli_cmd_obsidian._run_obsidian", return_value=(0, fake, "")):
            with capture_stdio() as (out, _err):
                code = run(["integrator", "obsidian", "tags", "counts", "--json"])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
        self.assertTrue(any(r.get("kind") == "obsidian_tag_count" for r in rows))
        self.assertTrue(any(r.get("kind") == "obsidian_tags_summary" for r in rows))

    def test_obsidian_attachments_report_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            notes = vault / "Notes"
            assets = vault / "Assets"
            notes.mkdir(parents=True)
            assets.mkdir(parents=True)
            (vault / ".obsidian").mkdir(parents=True)

            ok_img = assets / "used.png"
            ok_img.write_bytes(b"x")
            orphan = assets / "orphan.png"
            orphan.write_bytes(b"y")
            (notes / "n.md").write_text("![[Assets/used.png]]\n", encoding="utf-8")

            reports_dir = Path(td) / "reports"
            with capture_stdio() as (out, _err):
                code = run(
                    [
                        "integrator",
                        "obsidian",
                        "attachments",
                        "report",
                        "--vault-root",
                        str(vault),
                        "--reports-dir",
                        str(reports_dir),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            rows = [json.loads(line) for line in out.getvalue().splitlines() if line.strip()]
            summary = next(r for r in rows if r.get("kind") == "obsidian_attachments_report")
            report_json = Path(str(summary["report_json"]))
            self.assertTrue(report_json.exists())
            candidates = [r for r in rows if r.get("kind") == "obsidian_attachment_candidate"]
            self.assertEqual(len(candidates), 1)
            self.assertIn("Assets/orphan.png", candidates[0]["payload"]["rel"])

            backup_dir = Path(td) / "backup"
            with capture_stdio() as (out2, _err2):
                code2 = run(
                    [
                        "integrator",
                        "obsidian",
                        "attachments",
                        "delete",
                        "--vault-root",
                        str(vault),
                        "--report-json",
                        str(report_json),
                        "--backup-dir",
                        str(backup_dir),
                        "--apply",
                        "--json",
                    ]
                )
            self.assertEqual(code2, 0)
            self.assertFalse(orphan.exists())
            self.assertTrue((backup_dir / "Assets" / "orphan.png").exists())

    def test_obsidian_eval_disabled_without_enable(self) -> None:
        with capture_stdio() as (out, _err):
            code = run(["integrator", "obsidian", "eval", "--profile", "files_count", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out.getvalue().strip())
        self.assertEqual(payload["status"], "disabled")
