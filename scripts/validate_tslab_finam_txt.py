from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

EXPECTED_HEADER = [
    "<TICKER>",
    "<PER>",
    "<DATE>",
    "<TIME>",
    "<OPEN>",
    "<HIGH>",
    "<LOW>",
    "<CLOSE>",
    "<VOL>",
]


@dataclass
class FileCheck:
    path: Path
    ok: bool
    rows: int
    ticker: str
    per: str
    dt_min: str
    dt_max: str
    warnings: list[str]
    errors: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "ok": self.ok,
            "rows": self.rows,
            "ticker": self.ticker,
            "per": self.per,
            "dt_min": self.dt_min,
            "dt_max": self.dt_max,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _parse_dt(date_s: str, time_s: str) -> dt.datetime:
    ds = date_s.strip()
    ts = time_s.strip()

    if len(ds) == 8:
        d_fmt = "%Y%m%d"
    elif len(ds) == 6:
        d_fmt = "%y%m%d"
    else:
        raise ValueError(f"unsupported date format: {date_s!r}")

    if len(ts) == 6:
        t_fmt = "%H%M%S"
    elif len(ts) == 4:
        t_fmt = "%H%M"
    else:
        raise ValueError(f"unsupported time format: {time_s!r}")

    return dt.datetime.strptime(f"{ds}{ts}", d_fmt + t_fmt)


def validate_finam_txt(path: Path) -> FileCheck:
    warnings: list[str] = []
    errors: list[str] = []
    rows = 0
    ticker = ""
    per = ""
    dt_min = ""
    dt_max = ""
    prev_dt: dt.datetime | None = None

    if not path.exists():
        return FileCheck(path=path, ok=False, rows=0, ticker="", per="", dt_min="", dt_max="", warnings=[], errors=["missing_file"])

    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f, delimiter=",")
        try:
            header = next(r)
        except StopIteration:
            return FileCheck(path=path, ok=False, rows=0, ticker="", per="", dt_min="", dt_max="", warnings=[], errors=["empty_file"])

        if header != EXPECTED_HEADER:
            errors.append("invalid_header")

        for i, row in enumerate(r, start=2):
            if len(row) != 9:
                errors.append(f"bad_columns:line={i}:count={len(row)}")
                continue

            row_ticker, row_per, date_s, time_s, o, h, low, c, v = [x.strip() for x in row]
            if not ticker:
                ticker = row_ticker
            elif row_ticker != ticker:
                errors.append(f"ticker_changed:line={i}:{row_ticker}")

            if not per:
                per = row_per
            elif row_per != per:
                errors.append(f"per_changed:line={i}:{row_per}")

            try:
                ts = _parse_dt(date_s, time_s)
            except ValueError:
                errors.append(f"bad_datetime:line={i}")
                continue

            try:
                o_f = float(o)
                h_f = float(h)
                l_f = float(low)
                c_f = float(c)
                _ = float(v)
            except ValueError:
                errors.append(f"bad_numeric:line={i}")
                continue

            if h_f < max(o_f, c_f) or l_f > min(o_f, c_f) or h_f < l_f:
                warnings.append(f"ohlc_inconsistent:line={i}")

            if prev_dt is not None and ts < prev_dt:
                errors.append(f"time_not_monotonic:line={i}")
            prev_dt = ts

            if not dt_min:
                dt_min = ts.isoformat(sep=" ")
            dt_max = ts.isoformat(sep=" ")
            rows += 1

    if rows == 0:
        warnings.append("no_data_rows")

    ok = len(errors) == 0
    return FileCheck(
        path=path,
        ok=ok,
        rows=rows,
        ticker=ticker,
        per=per,
        dt_min=dt_min,
        dt_max=dt_max,
        warnings=warnings,
        errors=errors,
    )


def _default_root() -> Path:
    vault_root = Path(os.environ.get("VAULT_ROOT", r"C:\vault\Projects")).resolve()
    return vault_root / "AlgoTrading" / "TSLab" / "OfflineCSV" / "Finam_txt"


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validate Finam text files for TSLab provider")
    p.add_argument("--root", default=str(_default_root()))
    p.add_argument("--glob", default="*.txt")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(list(argv) if argv is not None else None)

    root = Path(args.root).resolve()
    files = sorted(root.glob(args.glob))
    checks = [validate_finam_txt(x) for x in files]

    payload = {
        "kind": "tslab_finam_txt_validation",
        "root": str(root),
        "files_total": len(checks),
        "files_ok": sum(1 for x in checks if x.ok),
        "files_failed": sum(1 for x in checks if not x.ok),
        "results": [x.as_dict() for x in checks],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"root={root}")
        print(f"files_total={payload['files_total']} files_ok={payload['files_ok']} files_failed={payload['files_failed']}")
        for row in checks:
            status = "OK" if row.ok else "FAIL"
            print(f"{status} {row.path.name}: rows={row.rows} ticker={row.ticker} per={row.per} dt_min={row.dt_min} dt_max={row.dt_max}")
            for w in row.warnings[:5]:
                print(f"  WARN {w}")
            for e in row.errors[:5]:
                print(f"  ERR {e}")

    return 0 if payload["files_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

