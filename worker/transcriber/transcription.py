"""Piano / polyphonic transcription via ByteDance's high-resolution model.

Kong et al. 2021 (`piano-transcription-inference`) hits MAESTRO onset-F1
0.967, compared to Basic Pitch's ~0.80, and specifically handles
re-articulations and offsets correctly — the failure modes we saw on real
piano recordings. MIT-licensed, ~160MB checkpoint, 20-40s CPU for 30s audio.
Basic Pitch is kept as a fallback when Kong fails or the content isn't
piano-like.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

import librosa
import pretty_midi


@contextlib.contextmanager
def _silence_stdout():
    with (
        open(os.devnull, "w") as devnull,
        contextlib.redirect_stdout(devnull),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        yield


def polyphonic_transcribe(wav_path: Path) -> pretty_midi.PrettyMIDI:
    """Transcribe audio to MIDI using Kong's piano transcription model.

    The model runs on raw 16kHz mono audio. Output is much cleaner than Basic
    Pitch: accurate onsets, proper offsets, no octave ghosts, reasonable
    velocity estimates. No downstream cleanup filters are needed — the model
    handles what the heuristics in the old pipeline were papering over.
    """
    from piano_transcription_inference import PianoTranscription

    audio, _ = librosa.load(str(wav_path), sr=16000, mono=True)

    tmp_midi = wav_path.with_suffix(".kong.mid")
    with _silence_stdout():
        transcriber = PianoTranscription(device="cpu", checkpoint_path=None)
        transcriber.transcribe(audio, str(tmp_midi))

    midi = pretty_midi.PrettyMIDI(str(tmp_midi))
    tmp_midi.unlink(missing_ok=True)
    return midi


def write_midi(midi: pretty_midi.PrettyMIDI, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(out_path))
    return out_path
