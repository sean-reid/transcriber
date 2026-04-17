# transcriber

Upload a short video, get back an MP4 of the clip with its audio written out as staff notation in a card below. Works for music and non-music.

## Layout

- `web/` - SvelteKit frontend (Cloudflare Pages)
- `worker/` - Python audio pipeline (Modal)
- `tests/` - Playwright end-to-end tests
- `infra/` - Cloudflare R2 bucket config

## Prerequisites

- Node 22+, pnpm 9+
- Python 3.12+, uv
- ffmpeg on PATH

## Setup

```
pnpm install
uv sync --directory worker
```

## Dev

```
pnpm dev          # web
pnpm worker:dev   # worker
pnpm test         # unit
pnpm test:e2e     # playwright
```

## Deploy

Cloudflare Pages deploys `web/` on push to `main`. Modal deploys `worker/` via `modal deploy`.
