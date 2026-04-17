"""Basic Pitch inference + MIDI post-processing."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

import pretty_midi
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict


@contextlib.contextmanager
def _silence_stdout():
    """Basic Pitch prints diagnostic shape/dtype lines to stdout. Swallow them."""
    with (
        open(os.devnull, "w") as devnull,
        contextlib.redirect_stdout(devnull),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        yield


def polyphonic_transcribe(wav_path: Path) -> pretty_midi.PrettyMIDI:
    """Run Basic Pitch on a mono WAV and return the parsed MIDI object."""
    with _silence_stdout():
        _model_output, midi_data, _note_events = predict(
            str(wav_path),
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=0.6,
            frame_threshold=0.4,
            minimum_note_length=120,
            minimum_frequency=55.0,
            maximum_frequency=2093.0,
            multiple_pitch_bends=False,
            melodia_trick=True,
        )
    _fill_small_gaps(midi_data)
    return midi_data


def _fill_small_gaps(midi: pretty_midi.PrettyMIDI, max_gap: float = 0.15) -> None:
    """Extend each note's end to the next note start when the gap is tiny.

    Basic Pitch tends to undershoot note durations by ~50-100 ms, which the
    music21 quantizer then renders as spurious eighth/sixteenth rests. Closing
    those gaps keeps the rhythm clean.
    """
    for instrument in midi.instruments:
        notes = sorted(instrument.notes, key=lambda n: n.start)
        for i, current in enumerate(notes[:-1]):
            following = notes[i + 1]
            gap = following.start - current.end
            if 0 < gap <= max_gap:
                current.end = following.start
        instrument.notes = notes


def write_midi(midi: pretty_midi.PrettyMIDI, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(out_path))
    return out_path
