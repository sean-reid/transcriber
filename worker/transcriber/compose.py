"""Composite source video + per-measure cards into a docked 65/35 MP4."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .rendering import MeasureCard

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1920
VIDEO_HEIGHT = 1248
CARD_HEIGHT = 672
FPS = 30
CROSSFADE_S = 0.12
SEPARATOR = 2  # divider thickness between video and score panel
PAPER = "0xFAF5EE"


def compose(video_in: Path, cards: list[MeasureCard], video_out: Path) -> Path:
    """Produce the final MP4 at 1080x1920 with video top, score cards bottom."""
    video_out.parent.mkdir(parents=True, exist_ok=True)

    if not cards:
        return _composite_without_cards(video_in, video_out)

    ordered = sorted(cards, key=lambda c: c.start_seconds)
    total_seconds = max(c.end_seconds for c in ordered)
    if total_seconds <= 0:
        return _composite_without_cards(video_in, video_out)

    args: list[str] = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_in)]

    for card in ordered:
        dur = max(0.1, card.end_seconds - card.start_seconds)
        args += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(card.png_path)]

    filter_parts: list[str] = []
    card_labels: list[str] = []
    for i, _ in enumerate(ordered, start=1):
        label = f"c{i}"
        filter_parts.append(
            f"[{i}:v]scale={OUTPUT_WIDTH}:{CARD_HEIGHT}:"
            f"force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{CARD_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color={PAPER},"
            f"format=yuv420p,fps={FPS}[{label}]"
        )
        card_labels.append(label)

    if len(card_labels) == 1:
        filter_parts.append(
            f"[{card_labels[0]}]trim=duration={total_seconds:.3f},setpts=PTS-STARTPTS[score]"
        )
    else:
        cumulative = ordered[0].end_seconds - ordered[0].start_seconds
        current = card_labels[0]
        for i in range(1, len(card_labels)):
            next_label = card_labels[i]
            offset = max(0.0, cumulative - CROSSFADE_S)
            out_label = f"mix{i}" if i < len(card_labels) - 1 else "score"
            filter_parts.append(
                f"[{current}][{next_label}]"
                f"xfade=transition=fade:duration={CROSSFADE_S}:offset={offset:.3f}[{out_label}]"
            )
            current = out_label
            segment = ordered[i].end_seconds - ordered[i].start_seconds
            cumulative += segment - CROSSFADE_S

    filter_parts.append(
        f"[0:v]scale={OUTPUT_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"format=yuv420p,fps={FPS}[top]"
    )
    filter_parts.append("[top][score]vstack=inputs=2[v]")

    filter_complex = ";".join(filter_parts)
    args += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        "-shortest",
        str(video_out),
    ]

    subprocess.run(args, check=True, capture_output=True)
    return video_out


def _composite_without_cards(video_in: Path, video_out: Path) -> Path:
    """Fallback: no score cards to overlay, just letterbox the source into 9:16."""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_in),
        "-vf",
        (
            f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"format=yuv420p,fps={FPS}"
        ),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        str(video_out),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return video_out
