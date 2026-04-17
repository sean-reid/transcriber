"""Classify an audio clip as music-like vs speech/noise.

The decision routes the pipeline to Basic Pitch (polyphonic) or pYIN
(monophonic contour), since Basic Pitch hallucinates on speech and pYIN is
cheaper and more accurate for a single voice.

Signal: mean spectral flatness, onset-strength density, and peak tempogram
prominence. Musical audio has lower flatness (more tonal energy), stronger
periodic onsets, and a prominent tempogram peak.
"""

from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np


@dataclass(frozen=True)
class ClassificationResult:
    is_music: bool
    flatness: float
    onset_density: float
    tempogram_peak: float


def classify(wav_path: str | bytes, sample_rate: int = 22050) -> ClassificationResult:
    y, sr = librosa.load(str(wav_path), sr=sample_rate, mono=True)

    flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_density = float(np.mean(onset_env))
    tempogram = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
    tempogram_peak = float(np.max(np.mean(tempogram, axis=1)))

    # Heuristic thresholds tuned on a handful of clips. Music tends to score
    # flatness < 0.15, onset_density > 1.5, tempogram_peak > 0.3. Any clear
    # tonal + rhythmic content trips "is_music" — borderline cases fall back
    # to the monophonic path, which also handles music fine at lower quality.
    is_music = flatness < 0.18 and onset_density > 1.0 and tempogram_peak > 0.25

    return ClassificationResult(
        is_music=is_music,
        flatness=flatness,
        onset_density=onset_density,
        tempogram_peak=tempogram_peak,
    )
