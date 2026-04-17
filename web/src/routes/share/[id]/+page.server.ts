import { error, redirect } from '@sveltejs/kit';
import { jobs } from '$lib/server/jobs';
import { services } from '$lib/server/services';
import type { PageServerLoad } from './$types';

const DOWNLOAD_TTL_SECONDS = 60 * 60;

export const load: PageServerLoad = async ({ params, platform }) => {
  const job = jobs().get(params.id);
  if (!job) error(404, 'job not found');

  const latest = job.events.at(-1);
  if (!latest || latest.stage !== 'done' || !latest.outputKey) {
    redirect(303, `/jobs/${params.id}`);
  }

  const { storage } = services(platform);
  const downloadUrl = await storage.publicUrl(latest.outputKey, DOWNLOAD_TTL_SECONDS);

  return {
    id: job.id,
    expiresAt: job.expiresAt,
    createdAt: job.createdAt,
    downloadUrl
  };
};
