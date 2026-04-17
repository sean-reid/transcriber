# infra

Manual setup notes for the Cloudflare side of the stack. One bucket, one Pages project, one Modal deploy.

## R2 bucket

Create a bucket named `transcriber`.

### CORS

```json
[
  {
    "AllowedOrigins": ["https://transcriber.pages.dev", "http://localhost:5173"],
    "AllowedMethods": ["GET", "PUT", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

Apply via dashboard or `wrangler r2 bucket cors set transcriber --file cors.json`.

### Lifecycle

Auto-delete after 24h. Apply via dashboard or wrangler:

```
Rule: expire-after-24h
Prefix: (empty, whole bucket)
Action: Delete objects, 1 day after creation
```

### Access keys

Create an R2 API token with read/write on the bucket. Store the keys in:

- Cloudflare Pages project environment: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.
- Modal secret named `transcriber-r2` with the same four variables.

## Cloudflare Pages

Project name: `transcriber`. Build command: `pnpm --filter web build`. Build output: `web/.svelte-kit/cloudflare`. Root directory: repo root.

## Modal

```
uv run --directory worker modal deploy app.py
```

The deploy prints an endpoint URL. Set it as `WORKER_URL` in the Pages environment.

## Domain

Cloudflare Registrar. Point a CNAME to the Pages project.
