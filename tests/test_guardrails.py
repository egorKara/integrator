from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import subprocess

import guardrails


class GuardrailsTests(unittest.TestCase):
    def _prepare_minimal_layout(self, root: Path) -> Path:
        (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (root / ".github" / "workflows" / "ci.yml").write_text(
            "name: ci\n# guardrails.py\n",
            encoding="utf-8",
        )

        algo = root / "vault" / "Projects" / "AlgoTrading"
        (algo / ".trae" / "rules").mkdir(parents=True, exist_ok=True)
        (algo / "Specs").mkdir(parents=True, exist_ok=True)
        (algo / "Configs").mkdir(parents=True, exist_ok=True)
        (algo / "README.md").write_text("ok", encoding="utf-8")
        (algo / "00-Rules (Summary).md").write_text("ok", encoding="utf-8")
        (algo / ".trae" / "rules" / "project_rules.md").write_text("ok", encoding="utf-8")
        (algo / "Specs" / "SPEC-001-Pipeline.md").write_text("ok", encoding="utf-8")
        (algo / "Configs" / "algotrading.json").write_text("{}", encoding="utf-8")

        localai = root / "LocalAI" / "assistant"
        (localai / ".trae" / "rules").mkdir(parents=True, exist_ok=True)
        (localai / ".trae" / "rules" / "project_rules.md").write_text("ok", encoding="utf-8")
        (localai / "README.md").write_text("ok", encoding="utf-8")

        scanned = root / "note.md"
        scanned.write_text("hello", encoding="utf-8")
        return scanned

    def test_run_guardrails_ok_on_minimal_layout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scanned = self._prepare_minimal_layout(root)
            payload = guardrails.run_guardrails(repo_root=root, paths=[scanned], strict=True)
            self.assertTrue(payload.get("ok"), msg=payload)

    def test_run_guardrails_detects_missing_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._prepare_minimal_layout(root)
            (root / "vault" / "Projects" / "AlgoTrading" / "Configs" / "algotrading.json").unlink()
            payload = guardrails.run_guardrails(repo_root=root, paths=[], strict=False)
            self.assertFalse(payload.get("ok"))
            errors = payload.get("errors", [])
            self.assertTrue(any("project_rules_coverage" in row.get("name", "") for row in errors))

    def test_run_guardrails_detects_secret_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scanned = self._prepare_minimal_layout(root)
            scanned.write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
            payload = guardrails.run_guardrails(repo_root=root, paths=[scanned], strict=False)
            self.assertFalse(payload.get("ok"))
            self.assertTrue(
                any(row.get("name") == "secret_scan_errors" for row in payload.get("errors", [])),
                msg=payload,
            )

    def test_run_guardrails_detects_secret_in_reports(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scanned = self._prepare_minimal_layout(root)
            reports = root / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            (reports / "x.md").write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
            payload = guardrails.run_guardrails(repo_root=root, paths=[scanned], strict=False, scan_reports=True)
            self.assertFalse(payload.get("ok"))
            self.assertTrue(
                any(row.get("name") == "secret_scan_reports_errors" for row in payload.get("errors", [])),
                msg=payload,
            )

    def test_run_guardrails_detects_secret_in_tracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            scanned = self._prepare_minimal_layout(root)
            subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
            docs = root / "docs"
            docs.mkdir(parents=True, exist_ok=True)
            (docs / "secret.md").write_text("-----BEGIN RSA PRIVATE KEY-----", encoding="utf-8")
            subprocess.run(["git", "add", "docs/secret.md"], cwd=str(root), check=True, capture_output=True)
            payload = guardrails.run_guardrails(repo_root=root, paths=[scanned], strict=False, scan_tracked=True)
            self.assertFalse(payload.get("ok"))
            self.assertTrue(
                any(row.get("name") == "secret_scan_tracked_errors" for row in payload.get("errors", [])),
                msg=payload,
            )


if __name__ == "__main__":
    unittest.main()
