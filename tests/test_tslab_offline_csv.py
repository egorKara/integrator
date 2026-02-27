import datetime as dt
import tempfile
import unittest
from pathlib import Path

from tslab_offline_csv import OhlcvBar, write_tslab_offline_csv, write_tslab_text_finam


class TSLabOfflineCsvTests(unittest.TestCase):
    def test_write_tslab_offline_csv_writes_semicolon_delimited_no_header(self) -> None:
        bars = [
            OhlcvBar(
                ts_utc=dt.datetime(2024, 1, 3, 0, 0, 0, tzinfo=dt.timezone.utc),
                open=271.9,
                high=274.7,
                low=271.0,
                close=274.56,
                volume=20586020.0,
            ),
            OhlcvBar(
                ts_utc=dt.datetime(2024, 1, 4, 0, 0, 0, tzinfo=dt.timezone.utc),
                open=274.56,
                high=276.1,
                low=273.5,
                close=275.0,
                volume=123.0,
            ),
        ]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "SBER_D1.csv"
            write_tslab_offline_csv(out, bars)
            text = out.read_text(encoding="utf-8")

        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0][0].isdigit())
        self.assertEqual(lines[0].count(";"), 6)
        self.assertNotIn(",", lines[0])
        self.assertIn("2024-01-03;00:00:00;", lines[0])

    def test_write_tslab_offline_csv_has_no_trailing_blank_lines(self) -> None:
        bar = OhlcvBar(
            ts_utc=dt.datetime(2024, 1, 3, 0, 0, 0, tzinfo=dt.timezone.utc),
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
            volume=10.0,
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "a.csv"
            write_tslab_offline_csv(out, [bar])
            raw = out.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))

    def test_write_tslab_text_finam_has_header_and_comma_format(self) -> None:
        bars = [
            OhlcvBar(
                ts_utc=dt.datetime(2026, 2, 27, 9, 0, 0, tzinfo=dt.timezone.utc),
                open=100.0,
                high=101.0,
                low=99.5,
                close=100.5,
                volume=1234.0,
            )
        ]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "RTS.txt"
            write_tslab_text_finam(out, bars, ticker="RTS", interval=1)
            lines = out.read_text(encoding="utf-8").splitlines()

        self.assertGreaterEqual(len(lines), 2)
        self.assertEqual(lines[0], "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>")
        self.assertTrue(lines[1].startswith("RTS,1,20260227,090000,"))
        self.assertIn(",100,101,99.5,100.5,1234", lines[1])


if __name__ == "__main__":
    unittest.main()
