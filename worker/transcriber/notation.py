"""MIDI to MusicXML via music21."""

from __future__ import annotations

from pathlib import Path

from music21 import clef, converter, expressions, key, metadata, meter, stream, tempo

MIDDLE_C_MIDI = 60


LONG_HOLD_SECONDS = 2.0


def midi_to_score(midi_path: Path, bpm: float | None = None) -> stream.Score:
    """Parse MIDI, quantize, split into treble/bass, return a music21 Score."""
    raw = converter.parse(
        str(midi_path),
        quantizePost=True,
        quarterLengthDivisors=(4,),
    )

    treble = stream.Part(id="treble")
    bass = stream.Part(id="bass")

    for element in raw.flatten().notes:
        destination = treble if element.pitches[0].midi >= MIDDLE_C_MIDI else bass
        destination.insert(element.offset, element)

    total_ql = max(
        (n.offset + n.duration.quarterLength for n in raw.flatten().notes),
        default=0.0,
    )

    if bpm is not None:
        treble.insert(0, tempo.MetronomeMark(number=float(bpm)))

    treble.insert(0, clef.TrebleClef())
    bass.insert(0, clef.BassClef())
    treble.insert(0, meter.TimeSignature("4/4"))
    bass.insert(0, meter.TimeSignature("4/4"))
    treble.insert(0, key.KeySignature(0))
    bass.insert(0, key.KeySignature(0))

    # Ensure both parts cover the same duration so makeMeasures produces
    # aligned bars. Filling with makeRests() yields a single rest per empty
    # measure instead of the spray of short rests you get from appending raw
    # rests from the flattened stream.
    for part in (treble, bass):
        if part.duration.quarterLength < total_ql:
            part.insert(total_ql - 0.01, stream.Voice())

    score = stream.Score(id="transcription")
    score.metadata = metadata.Metadata()
    score.metadata.title = ""
    score.metadata.composer = ""
    score.insert(0, treble)
    score.insert(0, bass)

    for part in (treble, bass):
        part.makeMeasures(inPlace=True)
        part.makeRests(inPlace=True, fillGaps=True, timeRangeFromBarDuration=True)
        part.makeNotation(inPlace=True)
        # Consolidate tied same-pitch chains into single longer notes so that,
        # e.g., two tied quarter notes become a half. Leaves ties alone when
        # the summed duration can't fit a single note value (respects meter).
        part.stripTies(inPlace=True, matchByPitch=True)

    _mark_long_holds(score, LONG_HOLD_SECONDS)
    return score


def _mark_long_holds(score: stream.Score, threshold_seconds: float) -> None:
    """Attach a fermata to the head of any tied chain (or rest) whose total
    duration is long enough that the reader should treat it as a hold.

    This is content-agnostic: applies equally to a 5-second sine-wave drone,
    a held vowel in speech, and a deliberately held note in a song.
    """
    for part in score.parts:
        chain_head = None
        chain_seconds = 0.0

        def seconds_for(element) -> float:
            try:
                return float(element.seconds)
            except Exception:
                return float(element.duration.quarterLength) * 0.5

        def close_chain():
            nonlocal chain_head, chain_seconds
            if (
                chain_head is not None
                and chain_seconds >= threshold_seconds
                and not any(isinstance(x, expressions.Fermata) for x in chain_head.expressions)
            ):
                chain_head.expressions.append(expressions.Fermata())
            chain_head = None
            chain_seconds = 0.0

        for element in part.recurse().notesAndRests:
            tie = getattr(element, "tie", None)
            tie_type = tie.type if tie is not None else None

            if tie_type in (None, "start"):
                close_chain()
                chain_head = element
                chain_seconds = seconds_for(element)
                if tie_type is None:
                    close_chain()
            elif tie_type in ("continue", "stop"):
                if chain_head is None:
                    chain_head = element
                chain_seconds += seconds_for(element)
                if tie_type == "stop":
                    close_chain()
        close_chain()


def write_musicxml(score: stream.Score, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out_path))
    return out_path
