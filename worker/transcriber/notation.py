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
    # aligned bars across both staves. When a part has no notes (e.g., Twinkle
    # plays only in the treble), insert an anchor rest at the end so the part
    # knows how long it should be.
    from music21 import note as m21note

    for part in (treble, bass):
        if part.duration.quarterLength < total_ql and total_ql > 0:
            anchor = m21note.Rest()
            anchor.quarterLength = max(total_ql - part.duration.quarterLength, 0.001)
            part.insert(part.duration.quarterLength, anchor)

    score = stream.Score(id="transcription")
    score.metadata = metadata.Metadata()
    score.metadata.title = ""
    score.metadata.composer = ""
    score.insert(0, treble)
    score.insert(0, bass)

    for part in (treble, bass):
        part.makeMeasures(inPlace=True)
        part.makeRests(inPlace=True, fillGaps=True, timeRangeFromBarDuration=True)
        # Consolidate tied same-pitch chains into single longer notes so that,
        # e.g., two tied quarter notes become a half. Runs before makeNotation
        # so makeNotation's re-tying respects the simplified durations.
        part.stripTies(inPlace=True, matchByPitch=True)
        part.makeNotation(inPlace=True)

    _mark_long_holds(score, LONG_HOLD_SECONDS)
    return score


def _mark_long_holds(score: stream.Score, threshold_seconds: float) -> None:
    """Attach a fermata to the head of any tied chain whose total duration
    exceeds the threshold, so the reader treats it as a hold. Works for
    sustained drones, held vowels, and held notes inside metered music.
    """
    ql_to_seconds = _detect_ql_to_seconds(score)

    for part in score.parts:
        elements = list(part.recurse().notes)  # notes only; rests are handled elsewhere
        i = 0
        while i < len(elements):
            head = elements[i]
            head_tie_type = head.tie.type if head.tie is not None else None
            if head_tie_type in ("continue", "stop"):
                i += 1
                continue

            total_seconds = float(head.duration.quarterLength) * ql_to_seconds
            j = i + 1
            while j < len(elements):
                nxt = elements[j]
                tie_type = nxt.tie.type if nxt.tie is not None else None
                if tie_type in ("continue", "stop"):
                    total_seconds += float(nxt.duration.quarterLength) * ql_to_seconds
                    if tie_type == "stop":
                        j += 1
                        break
                    j += 1
                else:
                    break

            if (
                total_seconds >= threshold_seconds
                and hasattr(head, "expressions")
                and not any(isinstance(x, expressions.Fermata) for x in head.expressions)
            ):
                head.expressions.append(expressions.Fermata())

            i = max(j, i + 1)


def _detect_ql_to_seconds(score: stream.Score) -> float:
    try:
        marks = list(score.recurse().getElementsByClass(tempo.MetronomeMark))
        if marks and marks[0].number:
            return 60.0 / float(marks[0].number)
    except Exception:
        pass
    return 0.5


def write_musicxml(score: stream.Score, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    score.write("musicxml", fp=str(out_path))
    return out_path
