import { error } from '@sveltejs/kit';
import { services } from '$lib/server/services';
import type { RequestHandler } from './$types';

const RANGE_RE = /^bytes=(\d*)-(\d*)$/;

function parseRange(header: string | null, size: number): { start: number; end: number } | null {
  if (!header) return null;
  const match = RANGE_RE.exec(header);
  if (!match) return null;
  const [, startStr, endStr] = match;
  let start = startStr ? Number(startStr) : NaN;
  let end = endStr ? Number(endStr) : NaN;
  if (Number.isNaN(start) && !Number.isNaN(end)) {
    start = Math.max(0, size - end);
    end = size - 1;
  } else if (Number.isNaN(end)) {
    end = size - 1;
  }
  if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end >= size || start > end) {
    return null;
  }
  return { start, end };
}

export const GET: RequestHandler = async ({ params, platform, request }) => {
  const { storage } = services(platform);
  const key = params.path;

  const total = await storage.size(key);
  if (total === null) error(404, 'not found');

  const range = parseRange(request.headers.get('range'), total);

  if (request.method === 'HEAD') {
    const object = await storage.get(key);
    if (!object) error(404, 'not found');
    return new Response(null, {
      headers: {
        'content-type': object.contentType,
        'content-length': String(total),
        'accept-ranges': 'bytes',
        'cache-control': 'private, max-age=60'
      }
    });
  }

  const object = await storage.get(key, range ?? undefined);
  if (!object) error(404, 'not found');

  const headers = new Headers({
    'content-type': object.contentType,
    'content-length': String(object.size),
    'accept-ranges': 'bytes',
    'cache-control': 'private, max-age=60'
  });

  if (range) {
    headers.set('content-range', `bytes ${range.start}-${range.end}/${total}`);
    return new Response(object.stream, { status: 206, headers });
  }

  return new Response(object.stream, { headers });
};

export const HEAD = GET;
