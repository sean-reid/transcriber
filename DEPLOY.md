# Deploy

One-shot production setup. All three pieces live on free or near-free tiers.

## 1. Cloudflare R2

```
wrangler r2 bucket create transcriber
wrangler r2 bucket cors set transcriber --file infra/cors.json
wrangler r2 bucket lifecycle add transcriber --prefix "" --expire-days 1
```

Create an R2 API token with read+write on the bucket. Note the four values:
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

## 2. Modal worker

```
cd worker
uv run modal token new    # one-time auth
uv run modal deploy app.py
```

The deploy prints a URL like `https://<slug>--transcriber-api.modal.run`.
Save it as `WORKER_URL`.

## 3. Cloudflare Pages

Create a Pages project pointing at this repo.

- Build command: `pnpm install --frozen-lockfile && pnpm --filter web build`
- Build output: `web/.svelte-kit/cloudflare`
- Root directory: `/`
- Environment variables (production):
  - `STORAGE_DRIVER=r2`
  - `WORKER_DRIVER=remote`
  - `R2_ACCOUNT_ID=...`
  - `R2_ACCESS_KEY_ID=...`
  - `R2_SECRET_ACCESS_KEY=...`
  - `R2_BUCKET=transcriber`
  - `WORKER_URL=https://...-transcriber-api.modal.run`

Push to `main`; Pages rebuilds automatically.

## Local dev

No cloud setup required. Defaults to local filesystem storage and a subprocess
worker:

```
pnpm dev
```

## Sanity checks after deploy

```
curl https://transcriber.pages.dev/
curl -X POST https://transcriber.pages.dev/api/jobs \
  -H "content-type: video/mp4" \
  --data-binary @tests/fixtures/sample.mp4
```

First response should include `{ "jobId": "..." }`.

The share link at `https://transcriber.pages.dev/share/<jobId>` plays within ~2–10s
after processing completes (depends on Modal cold start).
