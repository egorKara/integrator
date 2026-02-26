from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
ASSISTANT_ROOT = REPO_ROOT / "LocalAI" / "assistant"
ASSISTANT_BIN = ASSISTANT_ROOT / "bin"
VAULT_ALGO_ROOT = REPO_ROOT / "vault" / "Projects" / "AlgoTrading"


@dataclass(frozen=True)
class TranscriptMeta:
    session_id: str
    video_path: str
    audio_path: str
    transcript_json: str
    transcript_txt: str
    created_utc: str
    model_size: str
    language: str
    duration_sec: float | None
    segments: int
    text_len: int


def _utc_now() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds")


def _ensure_assistant_on_path() -> None:
    import sys

    sys.path.insert(0, str(ASSISTANT_ROOT.resolve()))
    os.environ["PATH"] = str(ASSISTANT_BIN.resolve()) + os.pathsep + os.environ.get("PATH", "")


def _ffprobe_duration(ffprobe_exe: Path, video_path: Path) -> float | None:
    cmd = [
        str(ffprobe_exe),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        return None
    try:
        return float(p.stdout.strip())
    except Exception:
        return None


def _extract_audio_wav(
    *,
    ffmpeg_exe: Path,
    video_path: Path,
    out_wav: Path,
) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg_exe),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(out_wav),
        "-y",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffmpeg failed")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-root", default=os.environ.get("ALGO_VIDEO_ROOT", r"C:\Video"))
    p.add_argument("--out-dir", default=str(VAULT_ALGO_ROOT / "Reports" / "TranscriptsFull"))
    p.add_argument("--tmp-dir", default=str(REPO_ROOT / ".tmp" / "video_full"))
    p.add_argument("--session-ids", default="")
    p.add_argument("--max-videos", type=int, default=0)
    p.add_argument("--model-size", default="base")
    p.add_argument("--language", default="ru")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    _ensure_assistant_on_path()
    AudioProcessor = getattr(
        importlib.import_module("app.services.algotrading.audio_processor"),
        "AudioProcessor",
    )

    ffmpeg_exe = ASSISTANT_BIN / "ffmpeg.exe"
    ffprobe_exe = ASSISTANT_BIN / "ffprobe.exe"
    video_root = Path(args.video_root)
    out_dir = Path(args.out_dir)
    tmp_dir = Path(args.tmp_dir)

    wanted = [s.strip() for s in args.session_ids.split(",") if s.strip()]
    if wanted:
        videos = [video_root / f"{sid}.mp4" for sid in wanted]
    else:
        videos = sorted([p for p in video_root.glob("*.mp4") if p.is_file()])

    videos = [v for v in videos if v.exists()]
    if args.max_videos and args.max_videos > 0:
        videos = videos[: args.max_videos]

    ap = AudioProcessor(model_size=args.model_size, device="cpu", compute_type="int8")

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    metas: list[TranscriptMeta] = []
    for v in videos:
        session_id = v.stem
        out_json = out_dir / f"{session_id}.transcript.json"
        out_txt = out_dir / f"{session_id}.transcript.txt"
        if out_json.exists() and out_txt.exists() and not args.force:
            try:
                payload = json.loads(out_json.read_text(encoding="utf-8"))
                metas.append(
                    TranscriptMeta(
                        session_id=session_id,
                        video_path=str(v),
                        audio_path=str(payload.get("audio_path", "")),
                        transcript_json=str(out_json),
                        transcript_txt=str(out_txt),
                        created_utc=str(payload.get("created_utc", "")),
                        model_size=str(payload.get("model_size", "")),
                        language=str(payload.get("language", "")),
                        duration_sec=payload.get("duration_sec"),
                        segments=len(payload.get("segments", []) or []),
                        text_len=len(payload.get("text", "") or ""),
                    )
                )
                continue
            except Exception:
                pass

        audio_wav = tmp_dir / "audio" / f"{session_id}.wav"
        _extract_audio_wav(ffmpeg_exe=ffmpeg_exe, video_path=v, out_wav=audio_wav)

        duration = _ffprobe_duration(ffprobe_exe, v)
        t_data: dict[str, Any] = ap.transcribe(audio_wav, language=args.language)
        payload = {
            "created_utc": _utc_now(),
            "session_id": session_id,
            "video_path": str(v),
            "audio_path": str(audio_wav),
            "model_size": args.model_size,
            "language": args.language,
            "duration_sec": duration,
            "segments": t_data.get("segments", []),
            "text": t_data.get("text", ""),
        }
        out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out_txt.write_text(payload["text"], encoding="utf-8")

        metas.append(
            TranscriptMeta(
                session_id=session_id,
                video_path=str(v),
                audio_path=str(audio_wav),
                transcript_json=str(out_json),
                transcript_txt=str(out_txt),
                created_utc=str(payload["created_utc"]),
                model_size=args.model_size,
                language=args.language,
                duration_sec=duration,
                segments=len(payload.get("segments", []) or []),
                text_len=len(payload.get("text", "") or ""),
            )
        )

    manifest = {
        "created_utc": _utc_now(),
        "video_root": str(video_root),
        "out_dir": str(out_dir),
        "model_size": args.model_size,
        "language": args.language,
        "items": [asdict(m) for m in metas],
    }
    stamp = dt.date.today().isoformat()
    (out_dir / f"manifest_{stamp}.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

