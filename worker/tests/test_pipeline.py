from pathlib import Path

import pytest

from transcriber import pipeline

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sample.mp4"


@pytest.mark.slow
def test_transcribe_produces_mp4_and_musicxml(tmp_path: Path):
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"

    events: list[tuple[str, dict]] = []

    def record(stage: str, extra: dict) -> None:
        events.append((stage, extra))

    result = pipeline.transcribe(FIXTURE, tmp_path, progress=record)

    assert result.mp4.exists()
    assert result.musicxml.exists()
    assert result.midi.exists()
    assert len(result.cards) > 0
    for card in result.cards:
        assert card.png_path.exists()
        assert card.end_seconds >= card.start_seconds

    stages = [s for s, _ in events]
    for expected in ("extracting", "detecting", "rendering", "encoding", "done"):
        assert expected in stages, f"{expected!r} missing from {stages!r}"

    xml = result.musicxml.read_text()
    assert "<score-partwise" in xml
