import tempfile
import unittest
from pathlib import Path

from scripts.validate_tslab_finam_txt import validate_finam_txt


class ValidateTslabFinamTxtTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
