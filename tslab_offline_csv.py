from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class OhlcvBar:
    ts_utc: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _fmt_float(x: float) -> str:
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    if s == "-0":
        return "0"
    return s


def _parse_moex_dt(value: str) -> dt.datetime:
    ts = dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return ts.replace(tzinfo=dt.timezone.utc)


def _finam_period_code(interval: int) -> str:
    mapping = {
        1: "1",
        5: "5",
        10: "10",
        15: "15",
        30: "30",
        60: "60",
        24: "D",
        7: "W",
        31: "M",
    }
    return mapping.get(interval, str(interval))


def fetch_moex_candles(
    *,
    secid: str,
    date_from: str,
    date_till: str,
    interval: int,
    engine: str = "stock",
    market: str = "shares",
) -> list[OhlcvBar]:
    start = 0
    step = 500
    raw_rows: list[Sequence[object]] = []
    cols: Sequence[str] | None = None

    while True:
        params = {
            "from": date_from,
            "till": date_till,
            "interval": str(interval),
            "start": str(start),
        }
        url = (
            f"https://iss.moex.com/iss/engines/{engine}/markets/{market}/securities/"
            f"{urllib.parse.quote(secid)}/candles.json?{urllib.parse.urlencode(params)}"
        )
        with urllib.request.urlopen(url, timeout=60) as r:
            payload = json.load(r)

        if cols is None:
            cols = payload["candles"]["columns"]

        page: Sequence[Sequence[object]] = payload["candles"]["data"]
        if not page:
            break

        raw_rows.extend(page)
        if len(page) < step:
            break
        start += len(page)

    if not cols:
        return []

    idx = {name: i for i, name in enumerate(cols)}
    out: list[OhlcvBar] = []
    for row in raw_rows:
        out.append(
            OhlcvBar(
                ts_utc=_parse_moex_dt(str(row[idx["begin"]])),
                open=float(str(row[idx["open"]])),
                high=float(str(row[idx["high"]])),
                low=float(str(row[idx["low"]])),
                close=float(str(row[idx["close"]])),
                volume=float(str(row[idx["volume"]])),
            )
        )

    out.sort(key=lambda b: b.ts_utc)
    return out


def write_tslab_offline_csv(path: Path, bars: Iterable[OhlcvBar]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        for b in bars:
            ts = b.ts_utc.astimezone(dt.timezone.utc)
            w.writerow(
                [
                    ts.strftime("%Y-%m-%d"),
                    ts.strftime("%H:%M:%S"),
                    _fmt_float(b.open),
                    _fmt_float(b.high),
                    _fmt_float(b.low),
                    _fmt_float(b.close),
                    _fmt_float(b.volume),
                ]
            )


def write_tslab_text_finam(
    path: Path,
    bars: Iterable[OhlcvBar],
    *,
    ticker: str,
    interval: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    per = _finam_period_code(interval)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>\n")
        for b in bars:
            ts = b.ts_utc
            row = [
                ticker,
                per,
                ts.strftime("%Y%m%d"),
                ts.strftime("%H%M%S"),
                _fmt_float(b.open),
                _fmt_float(b.high),
                _fmt_float(b.low),
                _fmt_float(b.close),
                _fmt_float(b.volume),
            ]
            f.write(",".join(row) + "\n")


def _cmd_moex(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(prog="tslab_offline_csv moex")
    p.add_argument("--secid", required=True)
    p.add_argument("--from", dest="date_from", required=True)
    p.add_argument("--till", dest="date_till", required=True)
    p.add_argument("--interval", type=int, required=True)
    p.add_argument("--engine", default="stock")
    p.add_argument("--market", default="shares")
    p.add_argument("--out", required=True)
    p.add_argument("--out-finam", default="")
    p.add_argument("--ticker", default="")
    args = p.parse_args(list(argv))

    secid = str(args.secid).strip().upper()
    ticker = str(args.ticker).strip().upper() if str(args.ticker).strip() else secid

    bars = fetch_moex_candles(
        secid=secid,
        date_from=args.date_from,
        date_till=args.date_till,
        interval=args.interval,
        engine=args.engine,
        market=args.market,
    )
    write_tslab_offline_csv(Path(args.out), bars)
    if str(args.out_finam).strip():
        write_tslab_text_finam(
            Path(args.out_finam),
            bars,
            ticker=ticker,
            interval=int(args.interval),
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Usage: tslab_offline_csv moex ...", file=sys.stderr)
        return 2

    cmd, rest = argv[0], argv[1:]
    if cmd == "moex":
        return _cmd_moex(rest)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
