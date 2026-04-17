import { error } from '@sveltejs/kit';
import { jobs, type JobEvent } from '$lib/server/jobs';
import type { RequestHandler } from './$types';

const TERMINAL = new Set(['done', 'failed']);

export const GET: RequestHandler = async ({ params }) => {
  const registry = jobs();
  const job = registry.get(params.id);
  if (!job) error(404, 'job not found');

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      const send = (event: JobEvent) => {
        const payload = `data: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(encoder.encode(payload));
      };
      const close = () => {
        try {
          controller.close();
        } catch {
          // already closed
        }
      };

      for (const event of job.events) {
        send(event);
      }
      const last = job.events.at(-1);
      if (last && TERMINAL.has(last.stage)) {
        close();
        return;
      }

      const unsubscribe = registry.subscribe(params.id, (event) => {
        send(event);
        if (TERMINAL.has(event.stage)) {
          unsubscribe();
          close();
        }
      });
    }
  });

  return new Response(stream, {
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-store',
      'x-accel-buffering': 'no'
    }
  });
};
