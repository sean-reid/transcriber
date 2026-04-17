import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import type { JobRegistry, Stage } from './jobs';
import type { LocalStorage } from './storage';

const STAGE_PAUSE_MS = 700;

export interface Worker {
  enqueue(jobId: string, inputKey: string): Promise<string>;
}

/**
 * Dev worker. Emits staged progress, then ffmpeg-copies the input to the
 * output key. The real transcription pipeline lands in phase 2.
 */
export class LocalWorker implements Worker {
  readonly #storage: LocalStorage;
  readonly #registry: JobRegistry;

  constructor(storage: LocalStorage, registry: JobRegistry) {
    this.#storage = storage;
    this.#registry = registry;
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
      for (const stage of ['extracting', 'detecting', 'rendering', 'encoding'] as Stage[]) {
        this.#registry.emit(jobId, { stage });
        await sleep(STAGE_PAUSE_MS);
      }

      const inputPath = this.#storage.localPath(inputKey);
      const outputPath = this.#storage.localPath(outputKey);
      await mkdir(dirname(outputPath), { recursive: true });
      await ffmpegCopy(inputPath, outputPath);

      this.#registry.emit(jobId, { stage: 'done', outputKey });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.#registry.emit(jobId, { stage: 'failed', message });
    }
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function ffmpegCopy(input: string, output: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      'ffmpeg',
      ['-y', '-i', input, '-c', 'copy', '-movflags', 'faststart', output],
      {
        stdio: ['ignore', 'ignore', 'pipe']
      }
    );
    let stderr = '';
    proc.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    proc.on('error', reject);
    proc.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`ffmpeg exited ${code}: ${stderr.slice(-200)}`));
    });
  });
}
