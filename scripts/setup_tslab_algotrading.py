from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

try:
    from tslab_offline_csv import fetch_moex_candles, write_tslab_offline_csv
except ModuleNotFoundError:
    _ROOT = Path(__file__).resolve().parents[1]
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from tslab_offline_csv import fetch_moex_candles, write_tslab_offline_csv


DEFAULT_SECIDS = ("SBER", "GAZP", "LKOH", "VTBR")
DEFAULT_TSLAB_EXE = Path(r"C:\Program Files\TSLab\TSLab 2.2\TSLab.exe")
VIDEO_CANON_LESSON_ID = "2026-01-03 15-13-36"
VIDEO_CANON_PROVIDER_NAME = "Finam_txt"
VIDEO_CANON_PROVIDER_TYPE_LABEL = "Текстовые файлы"
VIDEO_CANON_NOTE_NAME_TYPE = "TSLab — оффлайн поставщик данных (история) — Имя и Тип — 2026-02-24.md"
VIDEO_CANON_NOTE_FIELDS = "TSLab — оффлайн поставщик данных (история) — Настройки (поля) — 2026-02-24.md"


def _today_utc() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def _default_date_from() -> str:
    return (_today_utc() - dt.timedelta(days=365)).isoformat()


def _default_date_till() -> str:
    return _today_utc().isoformat()


def _default_algo_root() -> Path:
    env = os.environ.get("ALGO_VAULT_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    vault_root = Path(os.environ.get("VAULT_ROOT", r"C:\vault\Projects")).resolve()
    return (vault_root / "AlgoTrading").resolve()


def _video_source_notes(algo_root: Path) -> list[str]:
    notes_root = algo_root / "Notes"
    return [
        str((notes_root / VIDEO_CANON_NOTE_NAME_TYPE).resolve()),
        str((notes_root / VIDEO_CANON_NOTE_FIELDS).resolve()),
    ]


def _provider_ui_settings_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "exchange": str(args.exchange).strip(),
        "digits": int(args.digits),
        "money_digits": int(args.money_digits),
        "price_step": float(args.price_step),
        "lot_size": float(args.lot_size),
        "lot_step": float(args.lot_step),
        "currency": str(args.currency).strip(),
    }


def _fmt_numeric(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def _interval_label(interval: int) -> str:
    mapping = {1: "M1", 10: "M10", 60: "H1", 24: "D1", 7: "W1", 31: "MN1"}
    return mapping.get(interval, f"I{interval}")


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
    if not isinstance(obj, dict):
        return {}
    return obj


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def _write_runbook(
    *,
    path: Path,
    provider_name: str,
    provider_type_label: str,
    provider_ui_settings: dict[str, Any],
    offline_root: Path,
    manifest_path: Path,
    secids: list[str],
    interval: int,
    date_from: str,
    date_till: str,
    tslab_exe: Path,
    video_lesson_id: str,
    video_notes: list[str],
) -> None:
    lines: list[str] = []
    lines.append("# TSLab 2.2 — Каноничный запуск оффлайн-поставщика (по учебному видео)")
    lines.append("")
    lines.append(f"- video_lesson_id: `{video_lesson_id}`")
    for note_path in video_notes:
        lines.append(f"- video_note: `{note_path}`")
    lines.append(f"- provider_name: `{provider_name}`")
    lines.append(f"- provider_type: `{provider_type_label}`")
    lines.append(f"- offline_root: `{offline_root}`")
    lines.append(f"- manifest: `{manifest_path}`")
    lines.append(f"- symbols: `{', '.join(secids)}`")
    lines.append(f"- interval: `{interval}`")
    lines.append(f"- date_from: `{date_from}`")
    lines.append(f"- date_till: `{date_till}`")
    lines.append(f"- tslab_exe: `{tslab_exe}`")
    lines.append("")
    lines.append("## 1) Проверка файлов")
    lines.append("")
    lines.append("Убедись, что в `offline_root` созданы CSV в формате `date;time;open;high;low;close;volume` без заголовка.")
    lines.append("")
    lines.append("## 2) Настройка поставщика в TSLab (видео-канон)")
    lines.append("")
    lines.append("1. Открой `Данные -> Поставщики`.")
    lines.append(f"2. Нажми `Добавить` -> `{provider_type_label}`.")
    lines.append(f"3. Имя поставщика: `{provider_name}`.")
    lines.append(f"4. Папка: `{offline_root}`.")
    lines.append(f"5. Торговая площадка: `{provider_ui_settings['exchange'] or '(пусто)'}`.")
    lines.append(f"6. Количество знаков: `{provider_ui_settings['digits']}`.")
    lines.append(f"7. Количество денежных знаков: `{provider_ui_settings['money_digits']}`.")
    lines.append(f"8. Шаг цены: `{_fmt_numeric(float(provider_ui_settings['price_step']))}`.")
    lines.append(f"9. Размер лота: `{_fmt_numeric(float(provider_ui_settings['lot_size']))}`.")
    lines.append(f"10. Шаг лота: `{_fmt_numeric(float(provider_ui_settings['lot_step']))}`.")
    lines.append(f"11. Валюта: `{provider_ui_settings['currency']}`.")
    lines.append("12. Формат CSV: разделитель `;`, без заголовка, время в UTC.")
    lines.append("13. Сохрани и выбери поставщика в свойствах графика.")
    lines.append("")
    lines.append("## 3) Верификация")
    lines.append("")
    lines.append("1. Открой графики по символам из списка выше.")
    lines.append("2. Проверь, что свечи загружены за весь диапазон дат.")
    lines.append("3. Сделай первый backtest в учебном workspace.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _update_algotrading_config(
    *,
    algo_root: Path,
    tslab_exe: Path,
    offline_root: Path,
    manifest_path: Path,
    runbook_path: Path,
    secids: list[str],
    interval: int,
    date_from: str,
    date_till: str,
    provider_name: str,
    provider_type_label: str,
    provider_ui_settings: dict[str, Any],
    video_lesson_id: str,
    video_notes: list[str],
) -> Path:
    config_path = algo_root / "Configs" / "algotrading.json"
    cfg = _load_json(config_path)
    cfg["tslab"] = {
        "exe": str(tslab_exe),
        "offline_root": str(offline_root),
        "manifest": str(manifest_path),
        "runbook": str(runbook_path),
        "symbols": secids,
        "interval": interval,
        "date_from": date_from,
        "date_till": date_till,
        "provider": {
            "name": provider_name,
            "ui_type_label": provider_type_label,
            "ui_settings": provider_ui_settings,
        },
        "format": {
            "delimiter": ";",
            "timezone": "UTC",
            "has_header": False,
            "columns": ["date", "time", "open", "high", "low", "close", "volume"],
        },
        "video_canon": {
            "source": "training_video",
            "lesson_id": video_lesson_id,
            "notes": video_notes,
        },
    }
    _save_json(config_path, cfg)
    return config_path


def _download_moex_bundle(
    *,
    secids: list[str],
    date_from: str,
    date_till: str,
    interval: int,
    engine: str,
    market: str,
    offline_root: Path,
    overwrite: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    results: list[dict[str, Any]] = []
    warnings: list[str] = []
    label = _interval_label(interval)

    for secid in secids:
        out_csv = offline_root / f"{secid}_{label}.csv"
        if out_csv.exists() and not overwrite:
            results.append(
                {
                    "secid": secid,
                    "path": str(out_csv),
                    "status": "skipped_exists",
                    "bars": None,
                }
            )
            continue

        bars = fetch_moex_candles(
            secid=secid,
            date_from=date_from,
            date_till=date_till,
            interval=interval,
            engine=engine,
            market=market,
        )
        if not bars:
            warnings.append(f"no_bars:{secid}")
        write_tslab_offline_csv(out_csv, bars)
        results.append(
            {
                "secid": secid,
                "path": str(out_csv),
                "status": "written",
                "bars": len(bars),
            }
        )

    return results, warnings


def _launch_tslab(tslab_exe: Path) -> tuple[bool, str]:
    if not tslab_exe.exists():
        return False, f"tslab_exe_missing:{tslab_exe}"
    try:
        subprocess.Popen([str(tslab_exe)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def _cmd_moex(args: argparse.Namespace) -> int:
    algo_root = Path(args.algo_root).resolve()
    secid_input = args.secids if args.secids else list(DEFAULT_SECIDS)
    secids = [s.strip().upper() for s in secid_input if s.strip()]
    if not secids:
        print("--secid list is empty", file=sys.stderr)
        return 2

    offline_root = Path(args.offline_root).resolve() if args.offline_root else (algo_root / "TSLab" / "OfflineCSV" / "MOEX").resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else (algo_root / "TSLab" / "Manifests" / "offline_provider_moex.json").resolve()
    runbook_path = Path(args.runbook).resolve() if args.runbook else (algo_root / "TSLab" / "Runbooks" / "TSLab_Offline_Provider_Quickstart.md").resolve()
    tslab_exe = Path(args.tslab_exe).resolve()

    provider_name = str(args.provider_name).strip()
    provider_type_label = str(args.provider_type_label).strip()
    provider_ui_settings = _provider_ui_settings_from_args(args)
    video_lesson_id = str(args.video_lesson_id).strip()
    video_notes = [str(n).strip() for n in [args.video_note_1, args.video_note_2] if str(n).strip()]
    if not video_notes:
        video_notes = _video_source_notes(algo_root)

    offline_root.mkdir(parents=True, exist_ok=True)

    files, warnings = _download_moex_bundle(
        secids=secids,
        date_from=args.date_from,
        date_till=args.date_till,
        interval=int(args.interval),
        engine=str(args.engine),
        market=str(args.market),
        offline_root=offline_root,
        overwrite=bool(args.overwrite),
    )

    manifest: dict[str, Any] = {
        "kind": "tslab_moex_bundle",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "algo_root": str(algo_root),
        "provider": {
            "name": provider_name,
            "type": "text_offline",
            "ui_type_label": provider_type_label,
            "delimiter": ";",
            "timezone": "UTC",
            "has_header": False,
            "columns": ["date", "time", "open", "high", "low", "close", "volume"],
            "ui_settings": provider_ui_settings,
        },
        "canon": {
            "source": "training_video",
            "lesson_id": video_lesson_id,
            "notes": video_notes,
        },
        "source": {
            "name": "MOEX ISS",
            "engine": args.engine,
            "market": args.market,
            "date_from": args.date_from,
            "date_till": args.date_till,
            "interval": int(args.interval),
        },
        "files": files,
        "warnings": warnings,
    }
    _save_json(manifest_path, manifest)

    _write_runbook(
        path=runbook_path,
        provider_name=provider_name,
        provider_type_label=provider_type_label,
        provider_ui_settings=provider_ui_settings,
        offline_root=offline_root,
        manifest_path=manifest_path,
        secids=secids,
        interval=int(args.interval),
        date_from=args.date_from,
        date_till=args.date_till,
        tslab_exe=tslab_exe,
        video_lesson_id=video_lesson_id,
        video_notes=video_notes,
    )

    config_path = ""
    if not args.no_config_update:
        updated = _update_algotrading_config(
            algo_root=algo_root,
            tslab_exe=tslab_exe,
            offline_root=offline_root,
            manifest_path=manifest_path,
            runbook_path=runbook_path,
            secids=secids,
            interval=int(args.interval),
            date_from=args.date_from,
            date_till=args.date_till,
            provider_name=provider_name,
            provider_type_label=provider_type_label,
            provider_ui_settings=provider_ui_settings,
            video_lesson_id=video_lesson_id,
            video_notes=video_notes,
        )
        config_path = str(updated)

    launch_ok = None
    launch_error = ""
    if bool(args.launch_tslab):
        launch_ok, launch_error = _launch_tslab(tslab_exe)

    payload = {
        "kind": "tslab_setup_moex",
        "algo_root": str(algo_root),
        "offline_root": str(offline_root),
        "manifest": str(manifest_path),
        "runbook": str(runbook_path),
        "config_path": config_path,
        "provider_name": provider_name,
        "provider_type_label": provider_type_label,
        "provider_ui_settings": provider_ui_settings,
        "video_lesson_id": video_lesson_id,
        "video_notes": video_notes,
        "files": files,
        "warnings": warnings,
        "launch_tslab": bool(args.launch_tslab),
        "launch_ok": launch_ok,
        "launch_error": launch_error,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(f"manifest={manifest_path}")
        print(f"runbook={runbook_path}")
        print(f"offline_root={offline_root}")
        if config_path:
            print(f"config_path={config_path}")
        for row in files:
            print(f"{row['secid']}: {row['status']} bars={row['bars']} path={row['path']}")
        for w in warnings:
            print(f"WARN {w}")
        if args.launch_tslab:
            print(f"launch_ok={launch_ok} launch_error={launch_error}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare AlgoTrading TSLab offline workspace")
    sub = parser.add_subparsers(dest="cmd", required=True)

    moex = sub.add_parser("moex", help="Build MOEX offline CSV bundle for TSLab")
    moex.add_argument("--algo-root", default=str(_default_algo_root()))
    moex.add_argument("--secid", dest="secids", action="append", default=[])
    moex.add_argument("--from", dest="date_from", default=_default_date_from())
    moex.add_argument("--till", dest="date_till", default=_default_date_till())
    moex.add_argument("--interval", type=int, default=24)
    moex.add_argument("--engine", default="stock")
    moex.add_argument("--market", default="shares")
    moex.add_argument("--offline-root", default="")
    moex.add_argument("--manifest", default="")
    moex.add_argument("--runbook", default="")
    moex.add_argument("--provider-name", default=VIDEO_CANON_PROVIDER_NAME)
    moex.add_argument("--provider-type-label", default=VIDEO_CANON_PROVIDER_TYPE_LABEL)
    moex.add_argument("--exchange", default="")
    moex.add_argument("--digits", type=int, default=4)
    moex.add_argument("--money-digits", type=int, default=2)
    moex.add_argument("--price-step", type=float, default=0.0)
    moex.add_argument("--lot-size", type=float, default=1.0)
    moex.add_argument("--lot-step", type=float, default=1.0)
    moex.add_argument("--currency", default="Pt")
    moex.add_argument("--video-lesson-id", default=VIDEO_CANON_LESSON_ID)
    moex.add_argument("--video-note-1", default="")
    moex.add_argument("--video-note-2", default="")
    moex.add_argument("--tslab-exe", default=str(DEFAULT_TSLAB_EXE))
    moex.add_argument("--overwrite", action="store_true")
    moex.add_argument("--no-config-update", action="store_true")
    moex.add_argument("--launch-tslab", action="store_true")
    moex.add_argument("--json", action="store_true")
    moex.set_defaults(func=_cmd_moex)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

