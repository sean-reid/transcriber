import { error } from '@sveltejs/kit';
import { jobs } from '$lib/server/jobs';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
  const job = jobs().get(params.id);
  if (!job) error(404, 'job not found');

  const latest = job.events.at(-1);
  return {
    id: job.id,
    createdAt: job.createdAt,
    expiresAt: job.expiresAt,
    stage: latest?.stage ?? 'queued',
    outputKey: latest?.outputKey
  };
};
