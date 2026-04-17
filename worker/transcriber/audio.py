"""Audio I/O helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

SAMPLE_RATE = 22050


def extract_mono_wav(input_path: Path, output_wav: Path, sample_rate: int = SAMPLE_RATE) -> Path:
    """Extract mono audio from any video/audio container as PCM s16 WAV."""
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:a:0",
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        "-af",
        "aresample=async=1000",
        str(output_wav),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_wav


def copy_faststart(input_path: Path, output_mp4: Path) -> Path:
    """Remux input into a streaming-friendly MP4 without re-encoding."""
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_mp4
