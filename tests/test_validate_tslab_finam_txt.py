import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.validate_tslab_finam_txt as mod
from scripts.validate_tslab_finam_txt import validate_finam_txt


class ValidateTslabFinamTxtTests(unittest.TestCase):
    def test_parse_dt_supports_main_and_legacy_formats(self) -> None:
        ts1 = mod._parse_dt("20260105", "090000")
        ts2 = mod._parse_dt("260105", "0900")
        self.assertEqual(ts1.year, 2026)
        self.assertEqual(ts1.minute, 0)
        self.assertEqual(ts2.year, 2026)
        self.assertEqual(ts2.minute, 0)

    def test_parse_dt_raises_for_unsupported_formats(self) -> None:
        with self.assertRaises(ValueError):
            mod._parse_dt("2026-01-05", "090000")
        with self.assertRaises(ValueError):
            mod._parse_dt("20260105", "09:00")

    def test_missing_file_returns_error(self) -> None:
        p = Path(tempfile.gettempdir()) / "missing_finam_file_for_test.txt"
        r = validate_finam_txt(p)
        self.assertFalse(r.ok)
        self.assertIn("missing_file", r.errors)

    def test_empty_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.txt"
            p.write_text("", encoding="utf-8")
            r = validate_finam_txt(p)
        self.assertFalse(r.ok)
        self.assertIn("empty_file", r.errors)

    def test_accepts_yyyymmdd_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "RTS.txt"
            p.write_text(
                "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n"
                "RTS,1,20260105,090000,100,101,99,100.5,10\n"
                "RTS,1,20260105,090100,100.5,101,100,100.2,11\n",
                encoding="utf-8",
            )
            r = validate_finam_txt(p)

        self.assertTrue(r.ok)
        self.assertEqual(r.rows, 2)
        self.assertEqual(r.ticker, "RTS")
        self.assertEqual(r.dt_min, "2026-01-05 09:00:00")
        self.assertEqual(r.dt_max, "2026-01-05 09:01:00")

    def test_accepts_yymmdd_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "RTS_legacy.txt"
            p.write_text(
                "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n"
                "RTS,60,251126,090000,100,101,99,100.5,10\n"
                "RTS,60,251126,100000,100.5,101,100,100.2,11\n",
                encoding="utf-8",
            )
            r = validate_finam_txt(p)

        self.assertTrue(r.ok)
        self.assertEqual(r.rows, 2)
        self.assertEqual(r.per, "60")

    def test_reports_validation_errors_and_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.txt"
            p.write_text(
                "bad,header\n"
                "RTS,1,20260105,090000,100,101,99,100.5,10\n"
                "RTS,1,20260105\n"
                "MIX,1,20260105,090100,100.5,101,100,100.2,11\n"
                "MIX,5,20260105,090200,abc,101,100,100.2,11\n"
                "MIX,5,20260105,090300,100,95,99,96,11\n"
                "MIX,5,20260105,090250,100,101,99,100,11\n"
                "MIX,5,20260105,abcd00,100,101,99,100,11\n",
                encoding="utf-8",
            )
            r = validate_finam_txt(p)

        self.assertFalse(r.ok)
        self.assertIn("invalid_header", r.errors)
        self.assertTrue(any(x.startswith("bad_columns:line=3") for x in r.errors))
        self.assertTrue(any(x.startswith("ticker_changed:line=4:MIX") for x in r.errors))
        self.assertTrue(any(x.startswith("per_changed:line=5:5") for x in r.errors))
        self.assertTrue(any(x.startswith("bad_numeric:line=5") for x in r.errors))
        self.assertTrue(any(x.startswith("time_not_monotonic:line=7") for x in r.errors))
        self.assertTrue(any(x.startswith("bad_datetime:line=8") for x in r.errors))
        self.assertTrue(any(x.startswith("ohlc_inconsistent:line=6") for x in r.warnings))

    def test_no_data_rows_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "header_only.txt"
            p.write_text(
                "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n",
                encoding="utf-8",
            )
            r = validate_finam_txt(p)
        self.assertTrue(r.ok)
        self.assertIn("no_data_rows", r.warnings)

    def test_as_dict_contains_serializable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.txt"
            p.write_text(
                "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n"
                "RTS,1,20260105,090000,100,101,99,100.5,10\n",
                encoding="utf-8",
            )
            payload = validate_finam_txt(p).as_dict()
        self.assertEqual(payload["path"], str(p))
        self.assertEqual(payload["rows"], 1)
        self.assertIn("errors", payload)

    def test_default_root_uses_vault_root_env(self) -> None:
        with patch.dict(os.environ, {"VAULT_ROOT": r"C:\X\Vault"}, clear=False):
            root = mod._default_root()
        expected = Path(r"C:\X\Vault").resolve() / "AlgoTrading" / "TSLab" / "OfflineCSV" / "Finam_txt"
        self.assertEqual(root, expected)

    def test_main_json_output_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ok.txt"
            p.write_text(
                "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n"
                "RTS,1,20260105,090000,100,101,99,100.5,10\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                rc = mod.main(["--root", td, "--glob", "*.txt", "--json"])

        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["files_total"], 1)
        self.assertEqual(payload["files_failed"], 0)
        self.assertEqual(payload["results"][0]["ticker"], "RTS")

    def test_main_text_output_and_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.txt"
            p.write_text("bad,header\n", encoding="utf-8")
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                rc = mod.main(["--root", td, "--glob", "*.txt"])

        self.assertEqual(rc, 1)
        out = stdout.getvalue()
        self.assertIn("files_failed=1", out)
        self.assertIn("FAIL bad.txt:", out)


if __name__ == "__main__":
    unittest.main()
