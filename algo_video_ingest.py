from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoRecord:
    session_id: str
    video_path: str
    size_bytes: int
    mtime_utc: str
    sha256: str
    duration_s: float | None
    width: int | None
    height: int | None
    codec_video: str | None
    codec_audio: str | None
    spec_path: str | None
    spec_summary: str | None
    spec_terms: list[str]
    transcript_timestamps: int
    transcript_first_ts: str | None
    transcript_last_ts: str | None
    config_hints: list[str]
    images_dir: str | None
    images_found: int
    images_referenced: int
    images_missing: int


_RE_SUMMARY = re.compile(r"^## Summary\s*$", re.MULTILINE)
_RE_TERMS = re.compile(r"^## Terminology\s*$", re.MULTILINE)
_RE_SECTION = re.compile(r"^##\s+", re.MULTILINE)
_RE_IMAGE = re.compile(r"!\[\[(Projects/AlgoTrading/Assets/Images/[^\]]+?)\]\]")
_RE_TERM_LINE = re.compile(r"^\s*-\s+\*\*.+?\*\*:\s*(.+?)\s*$")
_RE_TS = re.compile(r"\*\*\((\d\d:\d\d:\d\d)\)\*\*")
_RE_HINT = re.compile(r"(таймфрейм|параметр|настро|шаг|stop|take|rsi|ma|ema|sma|grid|сетка)", re.IGNORECASE)

REPO_ROOT = Path(__file__).resolve().parent
VAULT_ALGO_ROOT = REPO_ROOT / "vault" / "Projects" / "AlgoTrading"
ASSISTANT_BIN = REPO_ROOT / "LocalAI" / "assistant" / "bin"


def _utc_iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe(path: Path, ffprobe_exe: Path) -> dict[str, Any]:
    cmd = [
        str(ffprobe_exe),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    return json.loads(p.stdout)


def _first_stream(payload: dict[str, Any], codec_type: str) -> dict[str, Any] | None:
    streams = payload.get("streams")
    if not isinstance(streams, list):
        return None
    for s in streams:
        if isinstance(s, dict) and s.get("codec_type") == codec_type:
            return s
    return None


def _to_int(x: Any) -> int | None:
    try:
        return int(x)
    except Exception:
        return None


def _to_float(x: Any) -> float | None:
    try:
        return float(x)
    except Exception:
        return None


def _extract_section(text: str, header_re: re.Pattern[str]) -> str | None:
    m = header_re.search(text)
    if not m:
        return None
    start = m.end()
    m2 = _RE_SECTION.search(text, start)
    end = m2.start() if m2 else len(text)
    out = text[start:end].strip()
    return out or None


def parse_spec(
    spec_path: Path,
) -> tuple[str | None, list[str], list[str], list[str], list[str]]:
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    summary = _extract_section(text, _RE_SUMMARY)
    terms_block = _extract_section(text, _RE_TERMS) or ""
    terms: list[str] = []
    for line in terms_block.splitlines():
        m = _RE_TERM_LINE.match(line)
        if m:
            terms.append(m.group(1).strip())
    images = [m.group(1) for m in _RE_IMAGE.finditer(text)]
    ts = [m.group(1) for m in _RE_TS.finditer(text)]

    hints_src = "\n".join([summary or "", terms_block]).strip()
    hints: list[str] = []
    for line in hints_src.splitlines():
        s = line.strip(" -\t")
        if not s:
            continue
        if _RE_HINT.search(s):
            if s not in hints:
                hints.append(s)

    return summary, terms, images, ts, hints


def _resolve_image_ref(vault_root: Path, ref: str) -> Path:
    normalized = ref.strip().replace("\\", "/")
    prefix = "Projects/AlgoTrading/"
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix) :]
    normalized = normalized.lstrip("/")
    return vault_root / Path(normalized)


def build_record(
    *,
    video_path: Path,
    vault_root: Path,
    ffprobe_exe: Path,
) -> VideoRecord:
    session_id = video_path.stem
    st = video_path.stat()
    digest = sha256_file(video_path)

    payload = ffprobe(video_path, ffprobe_exe)
    fmt = payload.get("format", {}) if isinstance(payload.get("format"), dict) else {}
    duration_s = _to_float(fmt.get("duration"))

    v = _first_stream(payload, "video") or {}
    a = _first_stream(payload, "audio") or {}
    width = _to_int(v.get("width"))
    height = _to_int(v.get("height"))
    codec_video = v.get("codec_name") if isinstance(v.get("codec_name"), str) else None
    codec_audio = a.get("codec_name") if isinstance(a.get("codec_name"), str) else None

    spec_path = vault_root / "Specs" / f"{session_id}.md"
    if spec_path.exists():
        summary, terms, images_refs, ts, hints = parse_spec(spec_path)
        images_dir = vault_root / "Assets" / "Images" / session_id
        images_found = 0
        if images_dir.exists():
            images_found = sum(1 for _ in images_dir.glob("*.jpg"))
        missing = 0
        for ref in images_refs:
            image_path = _resolve_image_ref(vault_root, ref)
            if not image_path.exists():
                missing += 1
        return VideoRecord(
            session_id=session_id,
            video_path=str(video_path),
            size_bytes=st.st_size,
            mtime_utc=_utc_iso(st.st_mtime),
            sha256=digest,
            duration_s=duration_s,
            width=width,
            height=height,
            codec_video=codec_video,
            codec_audio=codec_audio,
            spec_path=str(spec_path),
            spec_summary=summary,
            spec_terms=terms,
            transcript_timestamps=len(ts),
            transcript_first_ts=ts[0] if ts else None,
            transcript_last_ts=ts[-1] if ts else None,
            config_hints=hints,
            images_dir=str(images_dir) if images_dir.exists() else None,
            images_found=images_found,
            images_referenced=len(images_refs),
            images_missing=missing,
        )

    return VideoRecord(
        session_id=session_id,
        video_path=str(video_path),
        size_bytes=st.st_size,
        mtime_utc=_utc_iso(st.st_mtime),
        sha256=digest,
        duration_s=duration_s,
        width=width,
        height=height,
        codec_video=codec_video,
        codec_audio=codec_audio,
        spec_path=None,
        spec_summary=None,
        spec_terms=[],
        transcript_timestamps=0,
        transcript_first_ts=None,
        transcript_last_ts=None,
        config_hints=[],
        images_dir=None,
        images_found=0,
        images_referenced=0,
        images_missing=0,
    )


def write_manifest(path: Path, records: list[VideoRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_utc": dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds"),
        "video_root": str(Path(records[0].video_path).parent) if records else None,
        "records": [asdict(r) for r in records],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds_i = int(round(seconds))
    h, rem = divmod(seconds_i, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def write_report(path: Path, vault_root: Path, video_root: Path, records: list[VideoRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    missing_specs = [r for r in records if r.spec_path is None]
    missing_images = [r for r in records if r.images_referenced and r.images_missing]

    all_terms: dict[str, int] = {}
    for r in records:
        for t in r.spec_terms:
            all_terms[t] = all_terms.get(t, 0) + 1
    top_terms = sorted(all_terms.items(), key=lambda kv: (-kv[1], kv[0]))[:40]

    lines: list[str] = []
    lines.append("---")
    lines.append("project: AlgoTrading")
    lines.append("type: report")
    lines.append("status: draft")
    lines.append(f"created: {dt.date.today().isoformat()}")
    lines.append("tags: [video, ingest, algotrading]")
    lines.append("---")
    lines.append("")
    lines.append("# Ingest: C:\\Video → AlgoTrading (инвентаризация и извлечённые артефакты)")
    lines.append("")
    lines.append(f"- Vault: {vault_root}")
    lines.append(f"- Video root: {video_root}")
    lines.append(f"- Sessions found: {len(records)}")
    lines.append("")
    lines.append("## Сводка покрытий")
    lines.append(f"- Spec отсутствует: {len(missing_specs)}")
    lines.append(f"- Ссылки на изображения с пропусками: {len(missing_images)}")
    lines.append("")
    lines.append("## Инвентарь (видео → spec → images)")
    lines.append("")
    lines.append("| Session | Dur | WxH | Size(MB) | Timestamps | Spec | Images(found/ref/miss) | SHA256 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in sorted(records, key=lambda x: x.session_id):
        size_mb = r.size_bytes / (1024 * 1024)
        wh = f"{r.width or '?'}x{r.height or '?'}"
        spec_ok = "yes" if r.spec_path else "no"
        sha_short = r.sha256[:12]
        img_stats = f"{r.images_found}/{r.images_referenced}/{r.images_missing}"
        lines.append(
            f"| {r.session_id} | {_fmt_duration(r.duration_s)} | {wh} | {size_mb:.1f} | {r.transcript_timestamps} | {spec_ok} | {img_stats} | {sha_short} |"
        )
    lines.append("")
    lines.append("## Извлечённые термины/паттерны (из Terminology в Specs)")
    lines.append("")
    if top_terms:
        for term, cnt in top_terms:
            lines.append(f"- {term} (упоминаний: {cnt})")
    else:
        lines.append("- (нет данных)")
    lines.append("")
    lines.append("## Примечания по использованию в алгоритмической торговле")
    lines.append("- Specs уже содержат таймкоды и привязанные скриншоты; это пригодно для построения каталога паттернов и извлечения правил стратегии.")
    lines.append("- Для backtesting параметры (таймфрейм, уровни, stop/take, шаг сетки и т.п.) следует извлекать из Summary/Transcript и фиксировать отдельными атомарными заметками или JSON-манифестами.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-root", default=os.environ.get("ALGO_VIDEO_ROOT", r"C:\Video"))
    p.add_argument("--vault-root", default=str(VAULT_ALGO_ROOT))
    p.add_argument("--ffprobe", default=str(ASSISTANT_BIN / "ffprobe.exe"))
    p.add_argument("--out-dir", default=str(VAULT_ALGO_ROOT / "Reports"))
    args = p.parse_args()

    video_root = Path(args.video_root)
    vault_root = Path(args.vault_root)
    ffprobe_exe = Path(args.ffprobe)
    out_dir = Path(args.out_dir)

    videos = sorted([p for p in video_root.glob("*.mp4") if p.is_file()])
    records = [build_record(video_path=v, vault_root=vault_root, ffprobe_exe=ffprobe_exe) for v in videos]

    stamp = dt.date.today().isoformat()
    manifest_path = out_dir / f"video_ingest_manifest_{stamp}.json"
    report_path = out_dir / f"video_ingest_report_{stamp}.md"

    write_manifest(manifest_path, records)
    write_report(report_path, vault_root, video_root, records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
