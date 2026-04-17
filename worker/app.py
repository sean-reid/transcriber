"""Modal deployment.

Two entry points:
  * ``pipeline``: a plain Modal function that accepts raw input bytes and
    returns the rendered MP4 + MusicXML along with the stage log.
  * ``api``: a streaming ASGI endpoint that accepts a multipart upload and
    yields newline-delimited JSON stage events, with the final ``done`` event
    carrying base64-encoded output for same-call retrieval.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install(
        "numpy>=1.26,<2",
        "librosa>=0.10.2",
        "basic-pitch[onnx]>=0.4.0",
        "setuptools>=70,<75",
        "pretty_midi>=0.2.10",
        "music21>=9.3.0",
    )
    .add_local_python_source("transcriber")
)

app = modal.App("transcriber", image=image)


def _run(input_bytes: bytes) -> dict:
    """Write the upload to disk, run the pipeline, collect events, return result."""
    from transcriber import pipeline

    events: list[dict] = []

    def record(stage: str, extra: dict) -> None:
        events.append({"stage": stage, **extra})

    with tempfile.TemporaryDirectory() as work:
        work_path = Path(work)
        input_path = work_path / "input.bin"
        input_path.write_bytes(input_bytes)
        result = pipeline.transcribe(input_path, work_path / "out", progress=record)

        mp4 = result.mp4.read_bytes()
        xml = result.musicxml.read_text()

    return {
        "events": events,
        "mp4_base64": base64.b64encode(mp4).decode("ascii"),
        "musicxml": xml,
        "timings": dict(result.timings),
    }


@app.function(cpu=2, memory=2048, timeout=300)
def pipeline_fn(input_bytes: bytes) -> dict:
    """Direct Modal function: call via ``pipeline_fn.remote(bytes)``."""
    return _run(input_bytes)


@app.function(cpu=2, memory=2048, timeout=300)
@modal.asgi_app()
def api():
    from fastapi import FastAPI, UploadFile
    from fastapi.responses import StreamingResponse

    web = FastAPI(title="transcriber", version="0.1")

    @web.get("/health")
    async def health() -> dict:
        return {"ok": True}

    @web.post("/transcribe")
    async def transcribe(file: UploadFile):
        body = await file.read()

        def stream():
            events: list[dict] = []

            def record(stage: str, extra: dict) -> None:
                payload = {"stage": stage, **extra}
                events.append(payload)

            from transcriber import pipeline

            try:
                with tempfile.TemporaryDirectory() as work:
                    work_path = Path(work)
                    input_path = work_path / "input.bin"
                    input_path.write_bytes(body)
                    for payload in _iter_pipeline(pipeline, input_path, work_path / "out", record):
                        yield json.dumps(payload) + "\n"
            except Exception as err:
                yield json.dumps({"stage": "failed", "message": str(err)}) + "\n"

        return StreamingResponse(stream(), media_type="application/x-ndjson")

    return web


def _iter_pipeline(pipeline, input_path: Path, output_dir: Path, record):
    """Run the pipeline and emit each stage immediately."""
    from queue import Empty, Queue
    from threading import Thread

    queue: Queue = Queue()
    sentinel = object()

    def task() -> None:
        try:
            result = pipeline.transcribe(
                input_path, output_dir, progress=lambda s, e: queue.put({"stage": s, **e})
            )
            mp4 = result.mp4.read_bytes()
            xml = result.musicxml.read_text()
            queue.put(
                {
                    "stage": "done",
                    "mp4_base64": base64.b64encode(mp4).decode("ascii"),
                    "musicxml": xml,
                    "timings": dict(result.timings),
                }
            )
        except Exception as err:
            queue.put({"stage": "failed", "message": str(err)})
        queue.put(sentinel)

    thread = Thread(target=task, daemon=True)
    thread.start()

    while True:
        try:
            item = queue.get(timeout=1.0)
        except Empty:
            continue
        if item is sentinel:
            break
        yield item


@app.local_entrypoint()
def main() -> None:
    print("deploy with: uv run modal deploy app.py")
