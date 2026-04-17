"""Monophonic pitch transcription for speech, whistling, and sirens.

Uses librosa.pyin to extract a fundamental-frequency contour, snaps to
semitones, and segments into discrete note events via pitch-change and
voicing boundaries. Silence becomes rests and fermatas per the plan.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import pretty_midi

HOP = 512
FMIN = librosa.note_to_hz("C2")
FMAX = librosa.note_to_hz("C7")
MIN_NOTE_MS = 120
SEMITONE_JUMP = 2


def transcribe_monophonic(wav_path: Path, sample_rate: int = 22050) -> pretty_midi.PrettyMIDI:
    y, sr = librosa.load(str(wav_path), sr=sample_rate, mono=True)
    f0, _voiced_flag, voiced_prob = librosa.pyin(
        y,
        fmin=FMIN,
        fmax=FMAX,
        sr=sr,
        hop_length=HOP,
        fill_na=np.nan,
    )

    times = librosa.times_like(f0, sr=sr, hop_length=HOP)
    midi_float = librosa.hz_to_midi(f0)
    with np.errstate(invalid="ignore"):
        midi_snapped = np.round(midi_float)
    confident = (voiced_prob > 0.5) & ~np.isnan(midi_snapped)

    notes: list[pretty_midi.Note] = []
    current_pitch: int | None = None
    current_start: float | None = None
    current_velocity = 80

    for t, pitch, is_voiced in zip(times, midi_snapped, confident, strict=False):
        pitch_i = int(pitch) if is_voiced and not np.isnan(pitch) else None
        change = (
            pitch_i is None
            or current_pitch is None
            or abs(pitch_i - current_pitch) >= SEMITONE_JUMP
        )

        if change and current_pitch is not None and current_start is not None:
            end = float(t)
            if (end - current_start) * 1000 >= MIN_NOTE_MS:
                notes.append(
                    pretty_midi.Note(
                        velocity=current_velocity,
                        pitch=int(current_pitch),
                        start=current_start,
                        end=end,
                    )
                )
            current_pitch = None
            current_start = None

        if pitch_i is not None and current_pitch is None:
            current_pitch = pitch_i
            current_start = float(t)

    if current_pitch is not None and current_start is not None:
        end = float(times[-1]) if len(times) else current_start + MIN_NOTE_MS / 1000
        if (end - current_start) * 1000 >= MIN_NOTE_MS:
            notes.append(
                pretty_midi.Note(
                    velocity=current_velocity,
                    pitch=int(current_pitch),
                    start=current_start,
                    end=end,
                )
            )

    midi = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=0, name="voice")
    instrument.notes = notes
    midi.instruments.append(instrument)
    return midi
