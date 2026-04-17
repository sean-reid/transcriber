"""End-to-end transcription pipeline."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from . import audio, compose, notation, rendering, transcription


@dataclass(frozen=True)
class TranscribeResult:
    mp4: Path
    musicxml: Path
    midi: Path
    cards: list[rendering.MeasureCard]
    timings: dict[str, float]


def transcribe(
    input_path: Path,
    output_dir: Path,
    *,
    progress=None,
) -> TranscribeResult:
    """Run the full pipeline for a single clip.

    Emits progress events via the optional callback: ``progress(stage, extra)``.
    The caller is responsible for piping these to SSE or logs.
    """
    input_path = Path(input_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}

    def mark(stage: str, extra: dict | None = None) -> None:
        if progress is not None:
            progress(stage, extra or {})

    t0 = perf_counter()
    mark("extracting", {"label": "extracting audio"})
    wav_path = audio.extract_mono_wav(input_path, output_dir / "audio.wav")
    timings["extract"] = perf_counter() - t0

    t1 = perf_counter()
    mark("detecting", {"label": "detecting notes"})
    midi = transcription.polyphonic_transcribe(wav_path)
    midi_path = transcription.write_midi(midi, output_dir / "transcription.mid")
    note_count = sum(len(inst.notes) for inst in midi.instruments)
    timings["detect"] = perf_counter() - t1
    mark("detecting", {"notes": note_count})

    t2 = perf_counter()
    mark("rendering", {"label": "engraving notation"})
    score = notation.midi_to_score(midi_path)
    xml_path = notation.write_musicxml(score, output_dir / "transcription.musicxml")
    cards_dir = output_dir / "cards"
    cards = rendering.render_measure_cards(xml_path, cards_dir)
    timings["engrave"] = perf_counter() - t2
    mark("rendering", {"measures": len(cards)})

    t3 = perf_counter()
    mark("encoding", {"label": "encoding mp4"})
    normalized = audio.normalize_to_h264_aac(input_path, output_dir / "source.mp4")
    mp4_path = compose.compose(normalized, cards, output_dir / "output.mp4")
    timings["encode"] = perf_counter() - t3

    timings["total"] = perf_counter() - t0
    mark("done", {"mp4": str(mp4_path), "musicxml": str(xml_path), "timings": timings})

    return TranscribeResult(
        mp4=mp4_path, musicxml=xml_path, midi=midi_path, cards=cards, timings=timings
    )


def _emit_event(stage: str, extra: dict) -> None:
    payload = {"stage": stage, **extra}
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def cli(argv: list[str] | None = None) -> int:
    """Entry point: ``python -m transcriber <input> <output_dir>``."""
    import argparse

    parser = argparse.ArgumentParser(prog="transcriber")
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)

    try:
        transcribe(args.input, args.output_dir, progress=_emit_event)
    except Exception as err:
        _emit_event("failed", {"message": str(err)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
