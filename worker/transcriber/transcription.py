"""Basic Pitch inference + MIDI post-processing."""

from __future__ import annotations

import contextlib
import io
import os
from itertools import pairwise
from pathlib import Path

import librosa
import numpy as np
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
            frame_threshold=0.3,
            minimum_note_length=58,
            minimum_frequency=55.0,
            maximum_frequency=2093.0,
            multiple_pitch_bends=False,
            melodia_trick=True,
        )
    _split_missed_reonsets(midi_data, wav_path)
    _merge_same_pitch_repeats(midi_data)
    _drop_low_confidence(midi_data)
    _resolve_overlaps(midi_data)
    _reduce_to_melody(midi_data)
    _fill_small_gaps(midi_data)
    return midi_data


def _split_missed_reonsets(midi: pretty_midi.PrettyMIDI, wav_path: Path) -> None:
    """Use librosa onset detection to split Basic Pitch notes that actually
    contain multiple re-articulations the model missed.

    Basic Pitch is polyphonic-frame-first and tends to merge re-articulated
    same-pitch notes into one long held note (notably on repeated melody
    tones). A proper onset peak picker on the raw audio catches these.
    We split any note whose interior contains a strong onset peak.
    """
    try:
        y, sr = librosa.load(str(wav_path), sr=22050, mono=True)
    except Exception:
        return

    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        units="time",
        backtrack=True,
        delta=0.15,
        wait=3,
    )
    if onset_frames is None or len(onset_frames) == 0:
        return

    onsets = np.asarray(onset_frames, dtype=float)

    for instrument in midi.instruments:
        new_notes: list[pretty_midi.Note] = []
        for note in sorted(instrument.notes, key=lambda n: n.start):
            interior = onsets[(onsets > note.start + 0.08) & (onsets < note.end - 0.04)]
            if len(interior) == 0:
                new_notes.append(note)
                continue

            cuts = [note.start, *interior.tolist(), note.end]
            for a, b in pairwise(cuts):
                if b - a < 0.06:
                    continue
                new_notes.append(
                    pretty_midi.Note(
                        velocity=note.velocity,
                        pitch=note.pitch,
                        start=float(a),
                        end=float(b),
                    )
                )
        instrument.notes = new_notes


def _reduce_to_melody(midi: pretty_midi.PrettyMIDI, *, onset_window: float = 0.05) -> None:
    """Keep only the loudest note at each onset moment.

    Basic Pitch is polyphonic by design and emits every detected partial plus
    the chord tones the performer actually played. For a readable
    transcription we want ONE line: the melody. In real playing the melody
    is what the performer emphasizes — the loudest note in each moment.
    This collapses chord clusters to a single monophonic line that both
    tracks the tune and reads cleanly on a staff.

    Pure monophonic sources pass through unchanged (a cluster of one stays
    a cluster of one).
    """
    for instrument in midi.instruments:
        notes = sorted(instrument.notes, key=lambda n: (n.start, -n.velocity))
        clusters: list[list[pretty_midi.Note]] = []
        for note in notes:
            if clusters and abs(note.start - clusters[-1][0].start) <= onset_window:
                clusters[-1].append(note)
            else:
                clusters.append([note])

        kept: list[pretty_midi.Note] = []
        for cluster in clusters:
            # Loudest wins; ties break on longer duration, then higher pitch.
            cluster.sort(key=lambda n: (-n.velocity, -(n.end - n.start), -n.pitch))
            kept.append(cluster[0])
        kept.sort(key=lambda n: n.start)
        instrument.notes = kept


def _merge_same_pitch_repeats(midi: pretty_midi.PrettyMIDI, *, gap_threshold: float = 0.06) -> None:
    """Merge consecutive same-pitch notes with tiny gaps.

    Basic Pitch sometimes emits a second onset on a sustained note when the
    envelope dips briefly — these should be a single longer note, not two
    articulated ones. Gap threshold of 60ms is below a realistic restrike
    interval on any instrument.
    """
    for instrument in midi.instruments:
        by_pitch: dict[int, list[pretty_midi.Note]] = {}
        for note in instrument.notes:
            by_pitch.setdefault(note.pitch, []).append(note)

        kept: list[pretty_midi.Note] = []
        for notes in by_pitch.values():
            notes.sort(key=lambda n: n.start)
            current = notes[0]
            for nxt in notes[1:]:
                if nxt.start - current.end <= gap_threshold:
                    current.end = max(current.end, nxt.end)
                    current.velocity = max(current.velocity, nxt.velocity)
                else:
                    kept.append(current)
                    current = nxt
            kept.append(current)

        kept.sort(key=lambda n: n.start)
        instrument.notes = kept


def _drop_low_confidence(
    midi: pretty_midi.PrettyMIDI,
    *,
    min_duration_s: float = 0.07,
    velocity_z: float = -0.8,
) -> None:
    """Drop likely-noise notes: too short to be a real note AND well below
    the piece's own median velocity. Both conditions must hold so we don't
    discard fast passages of music that is genuinely quiet.
    """
    import numpy as np

    for instrument in midi.instruments:
        if not instrument.notes:
            continue
        velocities = np.array([n.velocity for n in instrument.notes], dtype=float)
        mean_v = float(velocities.mean())
        std_v = float(velocities.std()) or 1.0
        threshold_v = mean_v + velocity_z * std_v

        kept = []
        for note in instrument.notes:
            duration = note.end - note.start
            if duration < min_duration_s and note.velocity < threshold_v:
                continue
            kept.append(note)
        instrument.notes = kept


def _resolve_overlaps(midi: pretty_midi.PrettyMIDI) -> None:
    """When the same pitch is active twice at once, keep the louder note and
    drop the overlap. Basic Pitch occasionally emits a short ghost inside a
    held note — this collapses such cases cleanly.
    """
    for instrument in midi.instruments:
        by_pitch: dict[int, list[pretty_midi.Note]] = {}
        for note in instrument.notes:
            by_pitch.setdefault(note.pitch, []).append(note)

        kept: list[pretty_midi.Note] = []
        for notes in by_pitch.values():
            notes.sort(key=lambda n: n.start)
            for note in notes:
                overlapping = [
                    k
                    for k in kept
                    if k.pitch == note.pitch and k.end > note.start and k.start < note.end
                ]
                if not overlapping:
                    kept.append(note)
                    continue
                # Keep whichever is loudest; discard the rest.
                kept = [k for k in kept if k not in overlapping]
                candidates = [*overlapping, note]
                winner = max(candidates, key=lambda n: (n.velocity, n.end - n.start))
                kept.append(winner)

        kept.sort(key=lambda n: n.start)
        instrument.notes = kept


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
