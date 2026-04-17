"""Score rendering: MusicXML → per-measure PNG cards via Verovio + Playwright.

Each card shows a single measure. When a measure's last note has a tie that
extends into the next measure, the excerpt temporarily includes that next
measure so the tie arc can render correctly, then the card is cropped back to
the current measure's bounding box.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import verovio
from music21 import clef, converter, stream
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
  .card svg path {{ fill: currentColor; stroke: currentColor; }}
</style></head>
<body>
  <div class="card">{svg}</div>
</body></html>
"""


def _toolkit() -> verovio.toolkit:
    tk = verovio.toolkit()
    tk.setOptions(
        {
            "pageWidth": 1800,
            "pageHeight": 1120,
            "pageMarginTop": 20,
            "pageMarginBottom": 20,
            "pageMarginLeft": 20,
            "pageMarginRight": 20,
            "scale": 80,
            "font": "Leipzig",
            "breaks": "none",
            "adjustPageHeight": True,
            "adjustPageWidth": True,
            "shrinkToFit": True,
            "svgViewBox": True,
            "svgRemoveXlink": True,
            "smuflTextFont": "embedded",
            "systemDivider": "none",
            "header": "none",
            "footer": "none",
        }
    )
    return tk


def _measure_extends_into_next(score: stream.Score, measure_index: int) -> bool:
    """True when any note in this measure has a tie going forward."""
    excerpt = score.measures(
        measure_index,
        measure_index,
        collect=("Clef", "TimeSignature", "KeySignature", "Instrument"),
    )
    if excerpt is None:
        return False
    for note in excerpt.recurse().notes:
        tie = getattr(note, "tie", None)
        if tie is not None and tie.type in {"start", "continue"}:
            return True
    return False


def _excerpt_for_render(score: stream.Score, measure_index: int) -> stream.Score:
    """One measure, plus one-measure lookahead only when a tie forces it."""
    end = measure_index + 1 if _measure_extends_into_next(score, measure_index) else measure_index
    excerpt = score.measures(
        measure_index,
        end,
        collect=("Clef", "TimeSignature", "KeySignature", "Instrument"),
    )
    if excerpt is None:
        raise ValueError(f"measure {measure_index} missing")

    source_parts = list(score.parts) or [score]
    target_parts = list(excerpt.parts) or [excerpt]
    for src, tgt in zip(source_parts, target_parts, strict=False):
        first_measure = next(iter(tgt.getElementsByClass("Measure")), None)
        if first_measure is None:
            continue
        already = any(isinstance(e, clef.Clef) for e in first_measure.elements)
        if not already:
            src_clef = next(iter(src.recurse().getElementsByClass(clef.Clef)), None)
            if src_clef is not None:
                first_measure.insert(0, type(src_clef)())
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
                    excerpt = _excerpt_for_render(score, idx)
                    excerpt.write("musicxml", fp=str(tmp_xml))

                    tk = _toolkit()
                    xml_text = tmp_xml.read_text(encoding="utf-8")
                    if not tk.loadData(xml_text):
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
                        viewport={"width": CARD_WIDTH_PX * 2, "height": CARD_HEIGHT_PX * 2},
                        device_scale_factor=1,
                    )
                    page.set_content(html, wait_until="load")
                    png_path = output_dir / f"measure-{idx:03d}.png"
                    _screenshot_letterboxed(page, png_path)
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


def _screenshot_letterboxed(page, png_path: Path) -> None:
    """Screenshot the rendered SVG's actual content bounding box, then
    letterbox into a 1080x672 cream card. Verovio's SVG viewBox includes
    extra whitespace when the music is narrower than the page — we compute
    the real ink bounds and clip to that.
    """
    from PIL import Image

    bbox = page.evaluate(
        """() => {
          const svg = document.querySelector('.card svg');
          if (!svg) return null;
          const groups = svg.querySelectorAll('g.system, g.measure, g.staffGrp');
          if (!groups.length) {
            const r = svg.getBoundingClientRect();
            return { x: r.left, y: r.top, width: r.width, height: r.height };
          }
          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          groups.forEach(g => {
            const r = g.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return;
            minX = Math.min(minX, r.left);
            minY = Math.min(minY, r.top);
            maxX = Math.max(maxX, r.right);
            maxY = Math.max(maxY, r.bottom);
          });
          if (!isFinite(minX)) return null;
          const pad = 12;
          return {
            x: Math.max(0, minX - pad),
            y: Math.max(0, minY - pad),
            width: (maxX - minX) + pad * 2,
            height: (maxY - minY) + pad * 2,
          };
        }"""
    )
    if bbox is None:
        page.locator(".card").screenshot(path=str(png_path))
        return

    raw = png_path.with_suffix(".raw.png")
    page.screenshot(
        path=str(raw),
        clip={
            "x": bbox["x"],
            "y": bbox["y"],
            "width": max(bbox["width"], 16),
            "height": max(bbox["height"], 16),
        },
    )

    with Image.open(raw) as src:
        avail_w = CARD_WIDTH_PX - CARD_MARGIN * 2
        avail_h = CARD_HEIGHT_PX - CARD_MARGIN * 2
        scale = min(avail_w / src.width, avail_h / src.height, 4.0)
        target_w = max(1, int(src.width * scale))
        target_h = max(1, int(src.height * scale))
        resized = src.resize((target_w, target_h), Image.LANCZOS)

        card = Image.new("RGBA", (CARD_WIDTH_PX, CARD_HEIGHT_PX), (250, 245, 238, 255))
        off_x = (CARD_WIDTH_PX - target_w) // 2
        off_y = (CARD_HEIGHT_PX - target_h) // 2
        card.paste(resized, (off_x, off_y))
        card.convert("RGB").save(png_path, format="PNG", optimize=True)

    raw.unlink(missing_ok=True)
