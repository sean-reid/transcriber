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
    _strip_octave_ghosts(midi_data)
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


def _strip_octave_ghosts(
    midi: pretty_midi.PrettyMIDI,
    *,
    onset_window: float = 0.06,
    shorter_ratio: float = 0.6,
) -> None:
    """Remove notes that are exactly N octaves above a co-onset longer note.

    Basic Pitch often tags the 2nd/3rd harmonic of a fundamental as a short
    note one or two octaves above the real pitch. Real notes don't typically
    start at the same instant at exactly 12/24 semitones apart, so this is a
    safe cleanup.
    """
    for instrument in midi.instruments:
        # Sort by onset, then by pitch ascending so the fundamental is
        # considered before its octave partials at the same time.
        notes = sorted(instrument.notes, key=lambda n: (n.start, n.pitch))
        keep: list[pretty_midi.Note] = []
        for candidate in notes:
            cand_dur = candidate.end - candidate.start
            is_ghost = False
            for other in keep:
                if abs(other.start - candidate.start) > onset_window:
                    continue
                other_dur = other.end - other.start
                pitch_diff = candidate.pitch - other.pitch
                if pitch_diff in (12, 24) and cand_dur < shorter_ratio * other_dur:
                    is_ghost = True
                    break
            if not is_ghost:
                keep.append(candidate)
        instrument.notes = keep


def write_midi(midi: pretty_midi.PrettyMIDI, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(out_path))
    return out_path
