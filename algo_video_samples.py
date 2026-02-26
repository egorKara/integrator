from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import importlib
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent
ASSISTANT_ROOT = REPO_ROOT / "LocalAI" / "assistant"
ASSISTANT_BIN = ASSISTANT_ROOT / "bin"
VAULT_ALGO_ROOT = REPO_ROOT / "vault" / "Projects" / "AlgoTrading"


@dataclass(frozen=True)
class Sample:
    start_sec: float
    duration_sec: float
    text: str
    segments: list[dict[str, Any]]


@dataclass(frozen=True)
class VideoSamples:
    session_id: str
    video_path: str
    created_utc: str
    model_size: str
    sample_count: int
    samples: list[Sample]


def _utc_now() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat(timespec="seconds")


def _ensure_assistant_on_path() -> None:
    import sys

    sys.path.insert(0, str(ASSISTANT_ROOT.resolve()))
    os.environ["PATH"] = str(ASSISTANT_BIN.resolve()) + os.pathsep + os.environ.get("PATH", "")


def _run_ffmpeg_extract_wav(
    *,
    ffmpeg_exe: Path,
    video_path: Path,
    out_wav: Path,
    start_sec: float,
    duration_sec: float,
) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg_exe),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(max(0.0, start_sec)),
        "-t",
        str(max(1.0, duration_sec)),
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--video-root", default=os.environ.get("ALGO_VIDEO_ROOT", r"C:\Video"))
    p.add_argument("--out-dir", default=str(VAULT_ALGO_ROOT / "Reports"))
    p.add_argument("--tmp-dir", default=str(REPO_ROOT / ".tmp" / "video_samples"))
    p.add_argument("--model-size", default="base")
    p.add_argument("--segment-sec", type=float, default=30.0)
    p.add_argument("--positions", default="0,0.5")
    p.add_argument("--max-videos", type=int, default=0)
    p.add_argument("--out-name", default="")
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
    positions = [float(x.strip()) for x in args.positions.split(",") if x.strip()]

    ap = AudioProcessor(model_size=args.model_size, device="cpu", compute_type="int8")

    videos = sorted([p for p in video_root.glob("*.mp4") if p.is_file()])
    if args.max_videos and args.max_videos > 0:
        videos = videos[: args.max_videos]

    all_payload: dict[str, Any] = {
        "created_utc": _utc_now(),
        "video_root": str(video_root),
        "model_size": args.model_size,
        "segment_sec": args.segment_sec,
        "positions": positions,
        "items": [],
    }

    for v in videos:
        session_id = v.stem
        duration = _ffprobe_duration(ffprobe_exe, v)
        samples: list[Sample] = []
        for pos in positions:
            start = 0.0 if duration is None else max(0.0, min(duration - args.segment_sec, duration * pos))
            wav = tmp_dir / "audio" / f"{session_id}_{int(pos*100):03d}.wav"
            _run_ffmpeg_extract_wav(
                ffmpeg_exe=ffmpeg_exe,
                video_path=v,
                out_wav=wav,
                start_sec=start,
                duration_sec=args.segment_sec,
            )
            t = ap.transcribe(wav, language="ru")
            samples.append(
                Sample(
                    start_sec=round(float(start), 3),
                    duration_sec=round(float(args.segment_sec), 3),
                    text=t.get("text", ""),
                    segments=t.get("segments", []),
                )
            )

        item = VideoSamples(
            session_id=session_id,
            video_path=str(v),
            created_utc=_utc_now(),
            model_size=args.model_size,
            sample_count=len(samples),
            samples=samples,
        )
        all_payload["items"].append(asdict(item))

    stamp = dt.date.today().isoformat()
    out_name = args.out_name.strip()
    if not out_name:
        out_name = f"video_samples_{stamp}.json"
    out_path = out_dir / out_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
