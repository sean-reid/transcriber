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
            onset_threshold=0.5,
            frame_threshold=0.3,
            minimum_note_length=58,
            minimum_frequency=55.0,
            maximum_frequency=2093.0,
            multiple_pitch_bends=False,
            melodia_trick=True,
        )
    return midi_data


def write_midi(midi: pretty_midi.PrettyMIDI, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(out_path))
    return out_path
