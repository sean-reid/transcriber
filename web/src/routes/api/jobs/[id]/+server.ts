import { error, json } from '@sveltejs/kit';
import { jobs } from '$lib/server/jobs';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params }) => {
  const job = jobs().get(params.id);
  if (!job) error(404, 'job not found');

  const latest = job.events.at(-1);
  return json({
    id: job.id,
    createdAt: job.createdAt,
    expiresAt: job.expiresAt,
    stage: latest?.stage ?? 'queued',
    outputKey: latest?.outputKey,
    message: latest?.message
  });
};
