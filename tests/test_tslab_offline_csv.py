import datetime as dt
import io
import tempfile
import urllib.error
import unittest
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import tslab_offline_csv as mod
from tslab_offline_csv import OhlcvBar, write_tslab_offline_csv, write_tslab_text_finam


class _DummyResponse:
    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False


class TSLabOfflineCsvTests(unittest.TestCase):
    def test_fmt_float_and_period_code_helpers(self) -> None:
        self.assertEqual(mod._fmt_float(100.0), "100")
        self.assertEqual(mod._fmt_float(99.5000000000), "99.5")
        self.assertEqual(mod._fmt_float(-0.0), "0")
        self.assertEqual(mod._finam_period_code(24), "D")
        self.assertEqual(mod._finam_period_code(123), "123")

    def test_parse_moex_dt_returns_utc_datetime(self) -> None:
        ts = mod._parse_moex_dt("2026-03-01 12:34:56")
        self.assertEqual(ts.tzinfo, dt.timezone.utc)
        self.assertEqual(ts.isoformat(), "2026-03-01T12:34:56+00:00")

    def test_fetch_moex_candles_paginates_and_sorts(self) -> None:
        page_1_data = [
            ["2026-03-02 10:00:00", "11", "13", "10", "12", "100"],
            ["2026-03-02 09:00:00", "10", "12", "9", "11", "90"],
        ] + [[f"2026-03-02 11:{i % 60:02d}:00", "12", "13", "11", "12.5", "50"] for i in range(498)]
        payload_page_1 = {
            "candles": {
                "columns": ["begin", "open", "high", "low", "close", "volume"],
                "data": page_1_data,
            }
        }
        payload_page_2 = {
            "candles": {
                "columns": ["begin", "open", "high", "low", "close", "volume"],
                "data": [],
            }
        }
        urls: list[str] = []

        def fake_urlopen(url: str, timeout: int = 0) -> _DummyResponse:
            self.assertEqual(timeout, 60)
            urls.append(url)
            return _DummyResponse()

        with patch.object(mod.urllib.request, "urlopen", side_effect=fake_urlopen), patch.object(
            mod.json, "load", side_effect=[payload_page_1, payload_page_2]
        ):
            bars = mod.fetch_moex_candles(
                secid="SBER/P",
                date_from="2026-03-01",
                date_till="2026-03-10",
                interval=1,
            )

        self.assertEqual(len(bars), 500)
        self.assertEqual(bars[0].ts_utc.strftime("%H:%M:%S"), "09:00:00")
        self.assertIn("SBER/P/candles.json", urls[0])
        self.assertIn("start=0", urls[0])
        self.assertIn("start=500", urls[1])

    def test_fetch_moex_candles_empty_columns_returns_empty_list(self) -> None:
        payload: dict[str, Any] = {"candles": {"columns": [], "data": []}}
        with patch.object(mod.urllib.request, "urlopen", return_value=_DummyResponse()), patch.object(
            mod.json, "load", return_value=payload
        ):
            bars = mod.fetch_moex_candles(
                secid="SBER",
                date_from="2026-03-01",
                date_till="2026-03-10",
                interval=1,
            )
        self.assertEqual(bars, [])

    def test_fetch_moex_candles_stops_on_short_non_empty_page(self) -> None:
        payload = {
            "candles": {
                "columns": ["begin", "open", "high", "low", "close", "volume"],
                "data": [["2026-03-02 09:00:00", "10", "12", "9", "11", "90"]],
            }
        }
        with patch.object(mod.urllib.request, "urlopen", return_value=_DummyResponse()) as m_urlopen, patch.object(
            mod.json, "load", return_value=payload
        ):
            bars = mod.fetch_moex_candles(
                secid="SBER",
                date_from="2026-03-01",
                date_till="2026-03-10",
                interval=1,
            )
        self.assertEqual(len(bars), 1)
        m_urlopen.assert_called_once()

    def test_fetch_moex_candles_raises_on_missing_required_columns(self) -> None:
        payload = {
            "candles": {
                "columns": ["begin", "open"],
                "data": [["2026-03-02 09:00:00", "10"]],
            }
        }
        with patch.object(mod.urllib.request, "urlopen", return_value=_DummyResponse()), patch.object(
            mod.json, "load", return_value=payload
        ):
            with self.assertRaises(KeyError):
                mod.fetch_moex_candles(
                    secid="SBER",
                    date_from="2026-03-01",
                    date_till="2026-03-10",
                    interval=1,
                )

    def test_fetch_moex_candles_raises_on_invalid_numeric_value(self) -> None:
        payload = {
            "candles": {
                "columns": ["begin", "open", "high", "low", "close", "volume"],
                "data": [["2026-03-02 09:00:00", "bad", "12", "9", "11", "90"]],
            }
        }
        with patch.object(mod.urllib.request, "urlopen", return_value=_DummyResponse()), patch.object(
            mod.json, "load", return_value=payload
        ):
            with self.assertRaises(ValueError):
                mod.fetch_moex_candles(
                    secid="SBER",
                    date_from="2026-03-01",
                    date_till="2026-03-10",
                    interval=1,
                )

    def test_fetch_moex_candles_propagates_urlopen_error(self) -> None:
        with patch.object(mod.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(urllib.error.URLError):
                mod.fetch_moex_candles(
                    secid="SBER",
                    date_from="2026-03-01",
                    date_till="2026-03-10",
                    interval=1,
                )

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

    def test_write_tslab_offline_csv_converts_non_utc_to_utc(self) -> None:
        msk = dt.timezone(dt.timedelta(hours=3))
        bar = OhlcvBar(
            ts_utc=dt.datetime(2024, 1, 3, 3, 0, 0, tzinfo=msk),
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
            volume=10.0,
        )
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "tz.csv"
            write_tslab_offline_csv(out, [bar])
            line = out.read_text(encoding="utf-8").strip()
        self.assertIn("2024-01-03;00:00:00;", line)

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
            write_tslab_text_finam(out, bars, ticker="RTS", interval=24)
            lines = out.read_text(encoding="utf-8").splitlines()

        self.assertEqual(lines[0], "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>")
        self.assertTrue(lines[1].startswith("RTS,D,20260227,090000,"))
        self.assertIn(",100,101,99.5,100.5,1234", lines[1])

    def test_cmd_moex_calls_exporters_with_uppercase_values(self) -> None:
        with (
            patch.object(mod, "fetch_moex_candles", return_value=[]) as m_fetch,
            patch.object(mod, "write_tslab_offline_csv") as m_csv,
            patch.object(mod, "write_tslab_text_finam") as m_finam,
        ):
            rc = mod._cmd_moex(
                [
                    "--secid",
                    "sber",
                    "--from",
                    "2026-01-01",
                    "--till",
                    "2026-01-31",
                    "--interval",
                    "5",
                    "--out",
                    "out.csv",
                    "--out-finam",
                    "out.txt",
                    "--ticker",
                    " si ",
                ]
            )

        self.assertEqual(rc, 0)
        self.assertEqual(m_fetch.call_args.kwargs["secid"], "SBER")
        m_csv.assert_called_once()
        self.assertEqual(m_finam.call_args.kwargs["ticker"], "SI")

    def test_cmd_moex_uses_secid_as_default_ticker_and_skips_finam_file(self) -> None:
        with (
            patch.object(mod, "fetch_moex_candles", return_value=[]) as m_fetch,
            patch.object(mod, "write_tslab_offline_csv"),
            patch.object(mod, "write_tslab_text_finam") as m_finam,
        ):
            rc = mod._cmd_moex(
                [
                    "--secid",
                    "gazp",
                    "--from",
                    "2026-01-01",
                    "--till",
                    "2026-01-31",
                    "--interval",
                    "60",
                    "--out",
                    "out.csv",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(m_fetch.call_args.kwargs["secid"], "GAZP")
        m_finam.assert_not_called()

    def test_cmd_moex_whitespace_out_finam_skips_finam(self) -> None:
        with (
            patch.object(mod, "fetch_moex_candles", return_value=[]),
            patch.object(mod, "write_tslab_offline_csv"),
            patch.object(mod, "write_tslab_text_finam") as m_finam,
        ):
            rc = mod._cmd_moex(
                [
                    "--secid",
                    "gazp",
                    "--from",
                    "2026-01-01",
                    "--till",
                    "2026-01-31",
                    "--interval",
                    "60",
                    "--out",
                    "out.csv",
                    "--out-finam",
                    "   ",
                ]
            )
        self.assertEqual(rc, 0)
        m_finam.assert_not_called()

    def test_cmd_moex_parse_args_failures_raise_system_exit(self) -> None:
        with self.assertRaises(SystemExit) as miss_required:
            mod._cmd_moex([])
        self.assertEqual(miss_required.exception.code, 2)

        with self.assertRaises(SystemExit) as bad_interval:
            mod._cmd_moex(
                [
                    "--secid",
                    "SBER",
                    "--from",
                    "2026-01-01",
                    "--till",
                    "2026-01-31",
                    "--interval",
                    "abc",
                    "--out",
                    "x.csv",
                ]
            )
        self.assertEqual(bad_interval.exception.code, 2)

    def test_main_usage_and_unknown_command(self) -> None:
        stderr = io.StringIO()
        with patch.object(mod.sys, "stderr", stderr):
            self.assertEqual(mod.main([]), 2)
        self.assertIn("Usage:", stderr.getvalue())

        stderr = io.StringIO()
        with patch.object(mod.sys, "stderr", stderr):
            self.assertEqual(mod.main(["abc"]), 2)
        self.assertIn("Unknown command: abc", stderr.getvalue())

    def test_main_dispatches_to_moex_subcommand(self) -> None:
        with patch.object(mod, "_cmd_moex", return_value=7) as m_cmd:
            rc = mod.main(["moex", "--secid", "SBER"])
        self.assertEqual(rc, 7)
        m_cmd.assert_called_once_with(["--secid", "SBER"])


if __name__ == "__main__":
    unittest.main()
