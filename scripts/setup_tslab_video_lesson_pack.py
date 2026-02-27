from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Sequence

try:
    from tslab_offline_csv import fetch_moex_candles, write_tslab_offline_csv, write_tslab_text_finam
except ModuleNotFoundError:
    import sys
    _ROOT = Path(__file__).resolve().parents[1]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from tslab_offline_csv import fetch_moex_candles, write_tslab_offline_csv, write_tslab_text_finam

VIDEO_LESSON_ID = "2026-01-03 15-13-36"
VIDEO_PROVIDER_NAME = "Finam_txt"
DEFAULT_CONTRACTS: tuple[tuple[str, str], ...] = (
    ("RTS", "RIH6"),
    ("SBRF", "SRH6"),
    ("Si", "SiH6"),
)


def _today() -> str:
    return dt.date.today().isoformat()


def _default_date_from() -> str:
    return (dt.date.today() - dt.timedelta(days=60)).isoformat()


def _default_algo_root() -> Path:
    env = os.environ.get("ALGO_VAULT_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    vault_root = Path(os.environ.get("VAULT_ROOT", r"C:\vault\Projects")).resolve()
    return (vault_root / "AlgoTrading").resolve()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_contract_pair(raw: str) -> tuple[str, str]:
    value = str(raw).strip()
    if "=" not in value:
        raise ValueError(f"Invalid --contract value: {raw!r}, expected TICKER=SECID")
    left, right = value.split("=", 1)
    ticker = left.strip()
    secid = right.strip()
    if not ticker or not secid:
        raise ValueError(f"Invalid --contract value: {raw!r}, expected TICKER=SECID")
    return ticker, secid


def _build_contracts(raw_values: list[str] | None) -> list[tuple[str, str]]:
    if not raw_values:
        return list(DEFAULT_CONTRACTS)
    out: list[tuple[str, str]] = []
    for raw in raw_values:
        out.append(_parse_contract_pair(raw))
    return out


def _write_runbook(
    *,
    path: Path,
    provider_root: Path,
    contracts: list[tuple[str, str]],
    date_from: str,
    date_till: str,
) -> None:
    lines: list[str] = []
    lines.append("# TSLab — Учебный пакет данных по видеоуроку")
    lines.append("")
    lines.append(f"- lesson_id: `{VIDEO_LESSON_ID}`")
    lines.append(f"- provider_name: `{VIDEO_PROVIDER_NAME}`")
    lines.append(f"- provider_root: `{provider_root}`")
    lines.append(f"- period: `{date_from} .. {date_till}`")
    lines.append("")
    lines.append("## Что сгенерировано")
    for ticker, secid in contracts:
        lines.append(f"- `{ticker}.txt` (MOEX secid `{secid}`)")
    lines.append("")
    lines.append("## Настройка поставщика")
    lines.append("1. Данные -> Поставщики -> Добавить -> Текстовые файлы")
    lines.append("2. Имя: Finam_txt")
    lines.append(f"3. Папка: {provider_root}")
    lines.append("4. Торговая площадка: пусто")
    lines.append("5. Количество знаков: 4")
    lines.append("6. Количество денежных знаков: 2")
    lines.append("7. Шаг цены: 0")
    lines.append("8. Размер лота: 1")
    lines.append("9. Шаг лота: 1")
    lines.append("10. Валюта: Pt")
    lines.append("")
    lines.append("## Важно")
    lines.append("- Это учебный пакет на текущих контрактах MOEX (не склейка Finam за 2013+).")
    lines.append("- Для канона 1:1 по уроку (склейки) используй ручной экспорт Finam по 4 месяца.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Build TSLab training data pack aligned with video lesson")
    p.add_argument("--algo-root", default=str(_default_algo_root()))
    p.add_argument("--from", dest="date_from", default=_default_date_from())
    p.add_argument("--till", dest="date_till", default=_today())
    p.add_argument("--interval", type=int, default=1)
    p.add_argument("--engine", default="futures")
    p.add_argument("--market", default="forts")
    p.add_argument("--contract", action="append", default=[])
    p.add_argument("--provider-root", default="")
    p.add_argument("--manifest", default="")
    p.add_argument("--runbook", default="")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(list(argv) if argv is not None else None)

    algo_root = Path(args.algo_root).resolve()
    provider_root = (
        Path(args.provider_root).resolve()
        if str(args.provider_root).strip()
        else (algo_root / "TSLab" / "OfflineCSV" / VIDEO_PROVIDER_NAME).resolve()
    )
    manifest_path = (
        Path(args.manifest).resolve()
        if str(args.manifest).strip()
        else (algo_root / "TSLab" / "Manifests" / "video_lesson_training_pack.json").resolve()
    )
    runbook_path = (
        Path(args.runbook).resolve()
        if str(args.runbook).strip()
        else (algo_root / "TSLab" / "Runbooks" / "TSLab_Video_Training_Pack.md").resolve()
    )

    contracts = _build_contracts(list(args.contract) if args.contract else None)

    provider_root.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    warnings: list[str] = []

    for ticker, secid in contracts:
        txt_path = provider_root / f"{ticker}.txt"
        csv_path = provider_root / f"{ticker}.csv"
        if txt_path.exists() and not args.overwrite:
            files.append(
                {
                    "ticker": ticker,
                    "secid": secid,
                    "txt": str(txt_path),
                    "csv": str(csv_path),
                    "status": "skipped_exists",
                    "bars": None,
                }
            )
            continue

        bars = fetch_moex_candles(
            secid=secid,
            date_from=args.date_from,
            date_till=args.date_till,
            interval=int(args.interval),
            engine=str(args.engine),
            market=str(args.market),
        )
        if not bars:
            warnings.append(f"no_bars:{ticker}:{secid}")

        write_tslab_text_finam(
            txt_path,
            bars,
            ticker=ticker,
            interval=int(args.interval),
        )
        write_tslab_offline_csv(csv_path, bars)

        files.append(
            {
                "ticker": ticker,
                "secid": secid,
                "txt": str(txt_path),
                "csv": str(csv_path),
                "status": "written",
                "bars": len(bars),
            }
        )

    manifest: dict[str, Any] = {
        "kind": "tslab_video_training_pack",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "lesson_id": VIDEO_LESSON_ID,
        "provider_name": VIDEO_PROVIDER_NAME,
        "provider_root": str(provider_root),
        "source": {
            "engine": args.engine,
            "market": args.market,
            "interval": int(args.interval),
            "date_from": args.date_from,
            "date_till": args.date_till,
            "contracts": [{"ticker": t, "secid": s} for t, s in contracts],
        },
        "format": {
            "txt_header": "<TICKER>,<PER>,<DATE>,<TIME>,<OPEN>,<HIGH>,<LOW>,<CLOSE>,<VOL>",
            "txt_delimiter": ",",
            "csv_delimiter": ";",
        },
        "files": files,
        "warnings": warnings,
        "limitations": [
            "Uses current futures contracts from MOEX ISS, not Finam glued continuous series.",
            "For strict 1:1 lesson continuity since 2013 use manual Finam export in 4-month chunks.",
        ],
    }
    _save_json(manifest_path, manifest)

    _write_runbook(
        path=runbook_path,
        provider_root=provider_root,
        contracts=contracts,
        date_from=args.date_from,
        date_till=args.date_till,
    )

    cfg_path = algo_root / "Configs" / "algotrading.json"
    cfg = _load_json(cfg_path)
    cfg["tslab_video_training"] = {
        "provider_name": VIDEO_PROVIDER_NAME,
        "provider_root": str(provider_root),
        "manifest": str(manifest_path),
        "runbook": str(runbook_path),
        "lesson_id": VIDEO_LESSON_ID,
        "contracts": [{"ticker": t, "secid": s} for t, s in contracts],
        "date_from": args.date_from,
        "date_till": args.date_till,
        "interval": int(args.interval),
    }
    _save_json(cfg_path, cfg)

    out = {
        "kind": "tslab_video_training_pack_result",
        "provider_root": str(provider_root),
        "manifest": str(manifest_path),
        "runbook": str(runbook_path),
        "config": str(cfg_path),
        "files": files,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(f"provider_root={provider_root}")
        print(f"manifest={manifest_path}")
        print(f"runbook={runbook_path}")
        print(f"config={cfg_path}")
        for row in files:
            print(f"{row['ticker']}: {row['status']} bars={row['bars']} txt={row['txt']}")
        for w in warnings:
            print(f"WARN {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

