import type { JobRegistry, Stage } from './jobs';
import type { Storage } from './storage';

const STAGE_KEYS = new Set<Stage>([
  'queued',
  'uploading',
  'extracting',
  'detecting',
  'rendering',
  'encoding',
  'done',
  'failed'
]);

export interface Worker {
  enqueue(jobId: string, inputKey: string): Promise<string>;
}

/**
 * Streams the job through a Modal ASGI endpoint. Input is fetched from
 * storage and POSTed as multipart; stage events come back as NDJSON; the
 * final `done` event carries base64 MP4 bytes which get written back to
 * storage.
 */
export class RemoteWorker implements Worker {
  readonly #storage: Storage;
  readonly #registry: JobRegistry;
  readonly #workerUrl: string;

  constructor(storage: Storage, registry: JobRegistry, workerUrl: string) {
    this.#storage = storage;
    this.#registry = registry;
    this.#workerUrl = workerUrl.replace(/\/$/, '');
  }

  async enqueue(jobId: string, inputKey: string): Promise<string> {
    const outputKey = `output/${jobId}.mp4`;
    queueMicrotask(() => {
      void this.#run(jobId, inputKey, outputKey);
    });
    return outputKey;
  }

  async #run(jobId: string, inputKey: string, outputKey: string): Promise<void> {
    try {
      const input = await this.#storage.get(inputKey);
      if (!input) throw new Error(`input missing: ${inputKey}`);

      const body = new FormData();
      body.append(
        'file',
        new Blob([await new Response(input.stream).arrayBuffer()], {
          type: input.contentType
        }),
        'input.mp4'
      );

      const response = await fetch(`${this.#workerUrl}/transcribe`, {
        method: 'POST',
        body
      });
      if (!response.ok || !response.body) {
        throw new Error(`worker responded ${response.status}`);
      }

      await this.#pumpEvents(jobId, outputKey, response.body);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.#registry.emit(jobId, { stage: 'failed', message });
    }
  }

  async #pumpEvents(
    jobId: string,
    outputKey: string,
    stream: ReadableStream<Uint8Array>
  ): Promise<void> {
    type Event = {
      stage: string;
      mp4_base64?: string;
      message?: string;
      [key: string]: unknown;
    };

    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl = buffer.indexOf('\n');
      while (nl !== -1) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        nl = buffer.indexOf('\n');
        if (!line) continue;
        let event: Event;
        try {
          event = JSON.parse(line) as Event;
        } catch {
          continue;
        }

        if (event.stage === 'done' && event.mp4_base64) {
          await this.#storage.put(outputKey, _b64Stream(event.mp4_base64), 'video/mp4');
          this.#registry.emit(jobId, { stage: 'done', outputKey });
          continue;
        }

        if (event.stage === 'failed') {
          this.#registry.emit(jobId, {
            stage: 'failed',
            message: typeof event.message === 'string' ? event.message : 'failed'
          });
          continue;
        }

        if (STAGE_KEYS.has(event.stage as Stage)) {
          this.#registry.emit(jobId, { stage: event.stage as Stage });
        }
      }
    }
  }
}

function _b64Stream(base64: string): ReadableStream<Uint8Array> {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Response(bytes).body as ReadableStream<Uint8Array>;
}
