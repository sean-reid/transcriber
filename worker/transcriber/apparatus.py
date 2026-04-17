"""Decorate a music21 Score with notation apparatus derived from audio.

Adds dynamics, hairpins, tempo marking, accents, breath marks, and a final
barline, all from librosa features computed on the source WAV. Orthogonal to
the pitch-and-rhythm core; safe to call on any Score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
from music21 import (
    articulations,
    bar,
    dynamics,
    expressions,
    stream,
    tempo,
)
from music21 import (
    note as m21note,
)


@dataclass(frozen=True)
class AudioFeatures:
    y: np.ndarray
    sr: int
    rms_db: np.ndarray
    rms_times: np.ndarray
    onset_strength: np.ndarray
    onset_times: np.ndarray
    tempo_bpm: float
    total_seconds: float


DYNAMIC_STEPS: list[tuple[float, str]] = [
    (-55.0, "pp"),
    (-45.0, "p"),
    (-35.0, "mp"),
    (-25.0, "mf"),
    (-18.0, "f"),
    (-12.0, "ff"),
]

HAIRPIN_MIN_SECONDS = 0.8
HAIRPIN_MIN_DB = 6.0
ACCENT_ONSET_Z = 3.0
ACCENT_MAX_PER_MEASURE = 1
BREATH_GAP_SECONDS = 0.4


def analyze(wav_path: Path) -> AudioFeatures:
    y, sr = librosa.load(str(wav_path), sr=22050, mono=True)
    rms = librosa.feature.rms(y=y)[0]
    rms_db = librosa.amplitude_to_db(rms, ref=max(rms.max(), 1e-6))
    rms_times = librosa.times_like(rms, sr=sr, hop_length=512)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_times = librosa.times_like(onset_env, sr=sr, hop_length=512)

    bpm_arr = librosa.beat.tempo(y=y, sr=sr, aggregate=None)
    tempo_bpm = float(np.median(bpm_arr)) if len(bpm_arr) else 120.0

    return AudioFeatures(
        y=y,
        sr=sr,
        rms_db=rms_db,
        rms_times=rms_times,
        onset_strength=onset_env,
        onset_times=onset_times,
        tempo_bpm=tempo_bpm,
        total_seconds=float(len(y)) / sr,
    )


def decorate(score: stream.Score, features: AudioFeatures) -> stream.Score:
    _set_tempo(score, features.tempo_bpm)
    _set_final_barline(score)
    _apply_dynamics_per_measure(score, features)
    _apply_hairpins(score, features)
    _apply_accents(score, features)
    _apply_breath_marks(score, features)
    return score


def _set_tempo(score: stream.Score, bpm: float) -> None:
    if not (20 < bpm < 400):
        return
    rounded = int(round(bpm / 2) * 2)
    mark = tempo.MetronomeMark(number=rounded)
    parts = list(score.parts) or [score]
    first_measure = _first_measure(parts[0])
    target = first_measure if first_measure is not None else parts[0]
    target.insert(0, mark)


def _set_final_barline(score: stream.Score) -> None:
    for part in score.parts or [score]:
        measures = list(part.getElementsByClass("Measure"))
        if not measures:
            continue
        measures[-1].rightBarline = bar.Barline(type="final")


def _apply_dynamics_per_measure(score: stream.Score, features: AudioFeatures) -> None:
    for part in score.parts or [score]:
        prior_mark: str | None = None
        for measure in part.getElementsByClass("Measure"):
            start = _measure_start_seconds(measure)
            end = _measure_end_seconds(measure)
            db = _rms_db_in_range(features, start, end)
            if math.isnan(db):
                continue
            marking = _bucket_dynamic(db)
            if marking is None or marking == prior_mark:
                continue
            measure.insert(0, dynamics.Dynamic(marking))
            prior_mark = marking


def _apply_hairpins(score: stream.Score, features: AudioFeatures) -> None:
    trend = _dynamic_trend_segments(features, HAIRPIN_MIN_SECONDS, HAIRPIN_MIN_DB)
    if not trend:
        return
    parts = list(score.parts) or [score]
    anchor = parts[0]
    for seg_start, seg_end, direction in trend:
        first = _note_at_or_after(anchor, seg_start)
        last = _note_at_or_before(anchor, seg_end)
        if first is None or last is None or first is last:
            continue
        span_class = dynamics.Crescendo if direction > 0 else dynamics.Diminuendo
        span = span_class()
        span.addSpannedElements(first, last)
        anchor.insert(0, span)


def _apply_accents(score: stream.Score, features: AudioFeatures) -> None:
    if len(features.onset_strength) == 0:
        return
    threshold = float(np.mean(features.onset_strength)) + ACCENT_ONSET_Z * float(
        np.std(features.onset_strength)
    )
    strong_onsets = features.onset_times[features.onset_strength > threshold]
    if len(strong_onsets) == 0:
        return

    for part in score.parts or [score]:
        for measure in part.getElementsByClass("Measure"):
            added = 0
            for note in measure.recurse().notes:
                if added >= ACCENT_MAX_PER_MEASURE:
                    break
                t = _element_start_seconds(note)
                if t is None:
                    continue
                near = np.any(np.abs(strong_onsets - t) < 0.06)
                if near and not any(
                    isinstance(a, (articulations.Accent, articulations.StrongAccent))
                    for a in note.articulations
                ):
                    note.articulations.append(articulations.Accent())
                    added += 1


def _apply_breath_marks(score: stream.Score, features: AudioFeatures) -> None:
    silences = _silence_gaps(features, threshold_db=-40.0, min_gap=BREATH_GAP_SECONDS)
    if not silences:
        return
    parts = list(score.parts) or [score]
    anchor = parts[0]
    for gap_start, _ in silences:
        target = _note_at_or_before(anchor, gap_start)
        if target is None:
            continue
        if not any(isinstance(a, articulations.BreathMark) for a in target.articulations):
            target.articulations.append(articulations.BreathMark())


# -- helpers -----------------------------------------------------------------


def _first_measure(part: stream.Part) -> stream.Measure | None:
    for m in part.getElementsByClass("Measure"):
        return m
    return None


def _measure_start_seconds(measure: stream.Measure) -> float:
    site = measure.activeSite
    offset = measure.offset
    try:
        return float(site.offsetMap()[0].offset) + float(offset) * 0.5 if site else float(offset)
    except Exception:
        return float(offset) * 0.5


def _measure_end_seconds(measure: stream.Measure) -> float:
    return _measure_start_seconds(measure) + float(measure.duration.quarterLength) * 0.5


def _element_start_seconds(element) -> float | None:
    try:
        return float(element.getOffsetInHierarchy(element.activeSite)) * 0.5
    except Exception:
        try:
            return float(element.offset) * 0.5
        except Exception:
            return None


def _rms_db_in_range(features: AudioFeatures, start: float, end: float) -> float:
    mask = (features.rms_times >= start) & (features.rms_times < max(end, start + 1e-3))
    if not np.any(mask):
        return float("nan")
    return float(np.mean(features.rms_db[mask]))


def _bucket_dynamic(db: float) -> str | None:
    chosen: str | None = None
    for threshold, marking in DYNAMIC_STEPS:
        if db >= threshold:
            chosen = marking
    return chosen


def _dynamic_trend_segments(
    features: AudioFeatures, min_seconds: float, min_db: float
) -> list[tuple[float, float, int]]:
    if len(features.rms_db) == 0:
        return []
    window = max(1, int(min_seconds * features.sr / 512))
    smoothed = np.convolve(features.rms_db, np.ones(window) / window, mode="same")
    deltas = np.diff(smoothed)
    if len(deltas) == 0:
        return []

    segments: list[tuple[float, float, int]] = []
    sign = 0
    seg_start_idx = 0
    seg_start_db = smoothed[0]

    for i, d in enumerate(deltas):
        cur = 1 if d > 0 else (-1 if d < 0 else sign)
        if cur != sign and sign != 0:
            seg_end_idx = i
            db_delta = smoothed[seg_end_idx] - seg_start_db
            if abs(db_delta) >= min_db:
                t_start = float(features.rms_times[seg_start_idx])
                t_end = float(features.rms_times[seg_end_idx])
                if t_end - t_start >= min_seconds:
                    segments.append((t_start, t_end, sign))
            seg_start_idx = i
            seg_start_db = smoothed[i]
        sign = cur

    return segments


def _silence_gaps(
    features: AudioFeatures, threshold_db: float, min_gap: float
) -> list[tuple[float, float]]:
    quiet = features.rms_db < threshold_db
    if not np.any(quiet):
        return []

    gaps: list[tuple[float, float]] = []
    run_start: float | None = None
    for i, is_quiet in enumerate(quiet):
        t = float(features.rms_times[i])
        if is_quiet and run_start is None:
            run_start = t
        elif not is_quiet and run_start is not None:
            if t - run_start >= min_gap:
                gaps.append((run_start, t))
            run_start = None
    if run_start is not None:
        gaps.append((run_start, float(features.rms_times[-1])))
    return gaps


def _note_at_or_after(part: stream.Part, seconds: float) -> m21note.Note | None:
    for note in part.recurse().notes:
        t = _element_start_seconds(note)
        if t is not None and t >= seconds:
            return note
    return None


def _note_at_or_before(part: stream.Part, seconds: float) -> m21note.Note | None:
    last_match: m21note.Note | None = None
    for note in part.recurse().notes:
        t = _element_start_seconds(note)
        if t is not None and t <= seconds:
            last_match = note
    return last_match


__all__ = ["AudioFeatures", "analyze", "decorate"]


# Unused imports kept intentional for API consistency (future extensions).
_ = expressions
