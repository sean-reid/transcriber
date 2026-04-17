import { error } from '@sveltejs/kit';
import { services } from '$lib/server/services';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, platform, request }) => {
  const { storage } = services(platform);
  const key = params.path;

  const object = await storage.get(key);
  if (!object) error(404, 'not found');

  const headers = new Headers({
    'content-type': object.contentType,
    'content-length': String(object.size),
    'accept-ranges': 'bytes',
    'cache-control': 'private, max-age=60'
  });

  if (request.method === 'HEAD') {
    return new Response(null, { headers });
  }

  return new Response(object.stream, { headers });
};

export const HEAD = GET;
