import { error, json } from '@sveltejs/kit';
import { jobId as makeJobId } from '$lib/server/id';
import { jobs } from '$lib/server/jobs';
import { readEnv } from '$lib/server/env';
import { services } from '$lib/server/services';
import type { RequestHandler } from './$types';

const ALLOWED_TYPES = new Set(['video/mp4', 'video/quicktime', 'video/webm', 'video/x-matroska']);
const MAX_BYTES = 200 * 1024 * 1024;

export const POST: RequestHandler = async ({ request, platform }) => {
  const contentType = request.headers.get('content-type')?.split(';')[0]?.trim() ?? '';
  if (!ALLOWED_TYPES.has(contentType)) {
    error(415, `unsupported type: ${contentType || 'missing'}`);
  }

  const sizeHeader = request.headers.get('content-length');
  if (sizeHeader && Number(sizeHeader) > MAX_BYTES) {
    error(413, 'file too large');
  }

  if (!request.body) {
    error(400, 'empty body');
  }

  const id = makeJobId();
  const ext = contentType === 'video/quicktime' ? 'mov' : contentType.split('/')[1];
  const inputKey = `input/${id}.${ext}`;
  const env = readEnv(platform);
  const { storage, worker } = services(platform);

  await storage.put(inputKey, request.body, contentType);

  const registry = jobs();
  registry.create(id, inputKey, env.jobTtlSeconds);
  await worker.enqueue(id, inputKey);

  return json({ jobId: id }, { status: 202 });
};
