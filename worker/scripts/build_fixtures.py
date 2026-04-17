"""Generate known-ground-truth audio test fixtures as MP4 clips.

Each fixture is synthesized from a music21 Score so we can diff the pipeline's
output against the source score. Fixtures live under tests/fixtures/.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pretty_midi
from music21 import articulations, clef, expressions, key, meter, note, stream, tempo

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
SAMPLE_RATE = 44100


def synthesize_to_wav(score: stream.Score, out_wav: Path) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        midi_path = Path(tmp.name)
    score.write("midi", fp=str(midi_path))
    midi = pretty_midi.PrettyMIDI(str(midi_path))
    audio = _render_piano_like(midi, SAMPLE_RATE)
    audio = audio / max(np.max(np.abs(audio)), 1e-6) * 0.8
    pcm = (audio * 32767).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    _write_wav(out_wav, pcm, SAMPLE_RATE)
    midi_path.unlink(missing_ok=True)
    return out_wav


def _render_piano_like(midi: pretty_midi.PrettyMIDI, sr: int) -> np.ndarray:
    """Additive synthesis with a small harmonic stack + percussive decay.

    Closer to piano than a raw sine tone. Basic Pitch needs enough harmonic
    content to lock onto the fundamental reliably.
    """
    total = midi.get_end_time() + 0.3
    out = np.zeros(int(total * sr) + 1, dtype=np.float32)

    harmonics = np.array([1.0, 0.45, 0.28, 0.14, 0.08, 0.05], dtype=np.float32)

    for instrument in midi.instruments:
        for pm_note in instrument.notes:
            freq = 440.0 * (2 ** ((pm_note.pitch - 69) / 12))
            duration = max(pm_note.end - pm_note.start, 0.05)
            n_samples = int(duration * sr)
            t = np.arange(n_samples, dtype=np.float32) / sr
            sig = np.zeros(n_samples, dtype=np.float32)
            for k, amp in enumerate(harmonics, start=1):
                sig += amp * np.sin(2 * np.pi * freq * k * t)
            attack = int(0.008 * sr)
            release = int(0.05 * sr)
            env = np.ones(n_samples, dtype=np.float32)
            if attack < n_samples:
                env[:attack] = np.linspace(0, 1, attack, dtype=np.float32)
            env *= np.exp(-t * 1.6)
            if release < n_samples:
                env[-release:] *= np.linspace(1, 0, release, dtype=np.float32)
            sig *= env * (pm_note.velocity / 127.0)

            start_idx = int(pm_note.start * sr)
            end_idx = start_idx + n_samples
            if end_idx > out.size:
                end_idx = out.size
                sig = sig[: end_idx - start_idx]
            out[start_idx:end_idx] += sig

    return out


def _write_wav(path: Path, pcm: np.ndarray, sr: int) -> None:
    import wave

    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wav_to_mp4(wav: Path, mp4: Path, video_text: str = "") -> Path:
    """Wrap a WAV inside an MP4 with a simple 640x360 title card video."""
    mp4.parent.mkdir(parents=True, exist_ok=True)
    filter_video = (
        "color=c=#FAF5EE:s=640x360:d={d}:r=30,"
        "format=yuv420p,"
        "drawtext=fontfile=/System/Library/Fonts/Supplemental/Times\\ New\\ Roman.ttf:"
        f"text='{video_text}':fontcolor=#111111:fontsize=32:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
    )
    duration = _wav_duration(wav)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav),
        "-f",
        "lavfi",
        "-i",
        filter_video.format(d=f"{duration:.3f}"),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return mp4


def _wav_duration(wav: Path) -> float:
    import wave

    with wave.open(str(wav), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    return frames / float(rate)


# -- fixtures --------------------------------------------------------------


def twinkle_twinkle() -> stream.Score:
    """The canonical first line and first cadence."""
    melody = stream.Part(id="melody")
    melody.insert(0, clef.TrebleClef())
    melody.insert(0, meter.TimeSignature("4/4"))
    melody.insert(0, key.Key("C"))
    melody.insert(0, tempo.MetronomeMark(number=108))

    pitches = ["C4", "C4", "G4", "G4", "A4", "A4", "G4"]
    durations = [1, 1, 1, 1, 1, 1, 2]
    for pitch, ql in zip(pitches, durations, strict=False):
        n = note.Note(pitch)
        n.quarterLength = ql
        melody.append(n)

    for pitch, ql in zip(
        ["F4", "F4", "E4", "E4", "D4", "D4", "C4"], [1, 1, 1, 1, 1, 1, 2], strict=False
    ):
        n = note.Note(pitch)
        n.quarterLength = ql
        melody.append(n)

    score = stream.Score(id="twinkle")
    score.insert(0, melody)
    return score


def c_major_scale() -> stream.Score:
    melody = stream.Part(id="scale")
    melody.insert(0, clef.TrebleClef())
    melody.insert(0, meter.TimeSignature("4/4"))
    melody.insert(0, key.Key("C"))
    melody.insert(0, tempo.MetronomeMark(number=120))
    for pitch in ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]:
        n = note.Note(pitch)
        n.quarterLength = 0.5
        melody.append(n)
    score = stream.Score(id="scale")
    score.insert(0, melody)
    return score


def held_tone() -> stream.Score:
    """A single sustained A4. Exercises the fermata / 'ca. Ns' case."""
    part = stream.Part(id="drone")
    part.insert(0, clef.TrebleClef())
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=60))
    n = note.Note("A4")
    n.quarterLength = 5.0
    n.expressions.append(expressions.Fermata())
    part.append(n)
    score = stream.Score(id="drone")
    score.insert(0, part)
    return score


def accent_pattern() -> stream.Score:
    part = stream.Part(id="rhythm")
    part.insert(0, clef.TrebleClef())
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=120))
    for i in range(8):
        n = note.Note("E5")
        n.quarterLength = 0.5
        if i % 4 == 0:
            n.articulations.append(articulations.Accent())
        part.append(n)
    score = stream.Score(id="accent")
    score.insert(0, part)
    return score


FIXTURES = {
    "twinkle": (twinkle_twinkle, "Twinkle Twinkle"),
    "scale": (c_major_scale, "C major scale"),
    "drone": (held_tone, "Held A4"),
    "accent": (accent_pattern, "Accent pattern"),
}


def build_all() -> None:
    for name, (builder, caption) in FIXTURES.items():
        score = builder()
        wav = FIXTURES_DIR / f"{name}.wav"
        mp4 = FIXTURES_DIR / f"{name}.mp4"
        xml = FIXTURES_DIR / f"{name}.musicxml"
        synthesize_to_wav(score, wav)
        wav_to_mp4(wav, mp4, caption)
        score.write("musicxml", fp=str(xml))
        wav.unlink(missing_ok=True)
        print(
            f"wrote {mp4.relative_to(FIXTURES_DIR.parent)}, {xml.relative_to(FIXTURES_DIR.parent)}"
        )


if __name__ == "__main__":
    build_all()
