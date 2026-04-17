"""MIDI to MusicXML via music21."""

from __future__ import annotations

from pathlib import Path

from music21 import converter, key, meter, stream, tempo

MIDDLE_C_MIDI = 60


def midi_to_score(midi_path: Path, bpm: float | None = None) -> stream.Score:
    """Parse MIDI, quantize, split into treble/bass, return a music21 Score."""
    raw = converter.parse(
        str(midi_path),
        quantizePost=True,
        quarterLengthDivisors=(4, 3),
    )

    treble = stream.Part(id="treble")
    bass = stream.Part(id="bass")

    for element in raw.flatten().notes:
        destination = treble if element.pitches[0].midi >= MIDDLE_C_MIDI else bass
        destination.append(element)
    for rest in raw.flatten().notesAndRests:
        if rest.isRest:
            treble.append(rest)
            bass.append(rest)

    if bpm is not None:
        treble.insert(0, tempo.MetronomeMark(number=float(bpm)))

    treble.insert(0, meter.TimeSignature("4/4"))
    bass.insert(0, meter.TimeSignature("4/4"))
    treble.insert(0, key.KeySignature(0))
    bass.insert(0, key.KeySignature(0))

    score = stream.Score(id="transcription")
    score.insert(0, treble)
    score.insert(0, bass)

    for part in (treble, bass):
        part.makeMeasures(inPlace=True)
        part.makeNotation(inPlace=True)

    return score


def write_musicxml(score: stream.Score, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out_path))
    return out_path
