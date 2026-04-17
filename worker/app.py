"""Modal entry point. Real pipeline lands in phase 2."""

from __future__ import annotations

import modal

image = modal.Image.debian_slim(python_version="3.11").apt_install("ffmpeg")

app = modal.App("transcriber", image=image)


@app.function(cpu=2, memory=2048, timeout=120)
@modal.fastapi_endpoint(method="POST")
def transcribe(payload: dict) -> dict:
    """Accept a job reference, return a stub response."""
    input_key = payload.get("input_key")
    if not input_key:
        return {"error": "input_key required"}
    return {"status": "stub", "input_key": input_key}


@app.local_entrypoint()
def main() -> None:
    print("deploy with: modal deploy app.py")
