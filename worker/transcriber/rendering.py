"""Score rendering: MusicXML → per-measure PNG cards via Verovio + Playwright."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import verovio
from music21 import converter, stream
from playwright.sync_api import sync_playwright

CARD_WIDTH_PX = 1080
CARD_HEIGHT_PX = 672
CARD_MARGIN = 32
CARD_BG = "#FAF5EE"


@dataclass(frozen=True)
class MeasureCard:
    index: int
    png_path: Path
    start_seconds: float
    end_seconds: float


_HTML_TEMPLATE = """<!doctype html>
<html><head><style>
  html, body {{ margin: 0; padding: 0; background: {bg}; overflow: hidden; }}
  .card {{
    width: {width}px;
    height: {height}px;
    background: {bg};
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    padding: {pad}px;
    box-sizing: border-box;
  }}
  .card svg {{
    max-width: 100%;
    max-height: 100%;
    display: block;
  }}
  .card svg text {{ fill: #111; }}
  .card svg path {{ fill: #111; }}
</style></head>
<body>
  <div class="card">{svg}</div>
</body></html>
"""


def _toolkit() -> verovio.toolkit:
    tk = verovio.toolkit()
    tk.setOptions(
        {
            "pageWidth": 2160,
            "pageHeight": 1344,
            "pageMarginTop": 40,
            "pageMarginBottom": 40,
            "pageMarginLeft": 40,
            "pageMarginRight": 40,
            "scale": 60,
            "font": "Leipzig",
            "breaks": "none",
            "adjustPageHeight": True,
            "shrinkToFit": True,
            "svgViewBox": True,
            "svgRemoveXlink": True,
            "smuflTextFont": "embedded",
        }
    )
    return tk


def _excerpt_measure(score: stream.Score, measure_index: int) -> stream.Score:
    excerpt = score.measures(measure_index, measure_index, collect=[])
    if excerpt is None:
        raise ValueError(f"measure {measure_index} missing")
    return excerpt


def _measure_seconds(score: stream.Score) -> list[tuple[int, float, float]]:
    parts = list(score.parts) if score.parts else [score]
    anchor = parts[0]
    flat = anchor.flatten()
    tempo_map = flat.metronomeMarkBoundaries()

    def _cumulative_prior(boundary_start: float) -> float:
        total = 0.0
        for start_q, end_q, mark in tempo_map:
            if start_q >= boundary_start:
                break
            total += mark.durationToSeconds(end_q - start_q)
        return total

    def qn_to_sec(qn: float) -> float:
        for start_q, end_q, mark in tempo_map:
            if start_q <= qn <= end_q:
                return mark.durationToSeconds(qn - start_q) + _cumulative_prior(start_q)
        return qn * 0.5

    out: list[tuple[int, float, float]] = []
    for m in anchor.getElementsByClass("Measure"):
        start = qn_to_sec(m.offset)
        end = qn_to_sec(m.offset + m.duration.quarterLength)
        out.append((m.number, start, end))
    return out


def render_measure_cards(musicxml_path: Path, output_dir: Path) -> list[MeasureCard]:
    output_dir.mkdir(parents=True, exist_ok=True)
    score = converter.parse(str(musicxml_path))
    timings = _measure_seconds(score)
    tmp_xml = output_dir / "_excerpt.musicxml"

    cards: list[MeasureCard] = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=["--disable-web-security"])
            try:
                for idx, start, end in timings:
                    excerpt = _excerpt_measure(score, idx)
                    excerpt.write("musicxml", fp=str(tmp_xml))

                    tk = _toolkit()
                    if not tk.loadFile(str(tmp_xml)):
                        raise RuntimeError(f"verovio failed to load measure {idx}")
                    svg = tk.renderToSVG(1)

                    html = _HTML_TEMPLATE.format(
                        bg=CARD_BG,
                        width=CARD_WIDTH_PX,
                        height=CARD_HEIGHT_PX,
                        pad=CARD_MARGIN,
                        svg=svg,
                    )

                    page = browser.new_page(
                        viewport={"width": CARD_WIDTH_PX, "height": CARD_HEIGHT_PX},
                        device_scale_factor=1,
                    )
                    page.set_content(html, wait_until="load")
                    png_path = output_dir / f"measure-{idx:03d}.png"
                    page.locator(".card").screenshot(path=str(png_path), omit_background=False)
                    page.close()

                    cards.append(
                        MeasureCard(
                            index=idx, png_path=png_path, start_seconds=start, end_seconds=end
                        )
                    )
            finally:
                browser.close()
    finally:
        tmp_xml.unlink(missing_ok=True)

    return cards
