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

    stages = [s for s, _ in events]
    assert stages[:4] == ["extracting", "detecting", "rendering", "encoding"] or stages[:5] == [
        "extracting",
        "detecting",
        "detecting",
        "rendering",
        "encoding",
    ]
    assert stages[-1] == "done"

    xml = result.musicxml.read_text()
    assert "<score-partwise" in xml
