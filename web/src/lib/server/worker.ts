import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import type { JobRegistry, Stage } from './jobs';
import type { LocalStorage } from './storage';

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

/** Spawn the Python transcriber CLI and stream its stage events. */
export class LocalWorker implements Worker {
  readonly #storage: LocalStorage;
  readonly #registry: JobRegistry;
  readonly #workerDir: string;

  constructor(storage: LocalStorage, registry: JobRegistry, workerDir?: string) {
    this.#storage = storage;
    this.#registry = registry;
    this.#workerDir = workerDir ?? resolve(process.cwd(), '..', 'worker');
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
      const inputPath = this.#storage.localPath(inputKey);
      const outputPath = this.#storage.localPath(outputKey);
      const outputDir = dirname(outputPath);
      await mkdir(outputDir, { recursive: true });

      await this.#runPython(jobId, inputPath, outputDir, outputPath);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.#registry.emit(jobId, { stage: 'failed', message });
    }
  }

  #runPython(
    jobId: string,
    inputPath: string,
    outputDir: string,
    outputPath: string
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const proc = spawn(
        'uv',
        [
          'run',
          '--directory',
          this.#workerDir,
          'python',
          '-m',
          'transcriber',
          inputPath,
          outputDir
        ],
        { stdio: ['ignore', 'pipe', 'pipe'] }
      );

      let stdoutBuf = '';
      let stderrTail = '';

      proc.stdout.on('data', (chunk: Buffer) => {
        stdoutBuf += chunk.toString();
        let newlineIdx = stdoutBuf.indexOf('\n');
        while (newlineIdx !== -1) {
          const line = stdoutBuf.slice(0, newlineIdx).trim();
          stdoutBuf = stdoutBuf.slice(newlineIdx + 1);
          newlineIdx = stdoutBuf.indexOf('\n');
          if (!line) continue;
          this.#forwardEvent(jobId, line, outputPath).catch(() => {});
        }
      });

      proc.stderr.on('data', (chunk: Buffer) => {
        stderrTail = (stderrTail + chunk.toString()).slice(-400);
      });

      proc.on('error', reject);
      proc.on('close', (code) => {
        if (code === 0) resolve();
        else reject(new Error(`worker exited ${code}: ${stderrTail}`));
      });
    });
  }

  async #forwardEvent(jobId: string, line: string, outputPath: string): Promise<void> {
    type Event = {
      stage: string;
      mp4?: string;
      musicxml?: string;
      message?: string;
      [key: string]: unknown;
    };
    let event: Event;
    try {
      event = JSON.parse(line) as Event;
    } catch {
      return;
    }
    if (!STAGE_KEYS.has(event.stage as Stage)) return;

    if (event.stage === 'done') {
      if (event.mp4) {
        const buf = await readFile(event.mp4);
        await writeFile(outputPath, buf);
      }
      const meta = outputPath + '.meta.json';
      await writeFile(meta, JSON.stringify({ contentType: 'video/mp4' }), 'utf8');
      this.#registry.emit(jobId, {
        stage: 'done',
        outputKey: outputPath.split('/').slice(-2).join('/')
      });
      return;
    }

    if (event.stage === 'failed') {
      this.#registry.emit(jobId, {
        stage: 'failed',
        message: typeof event.message === 'string' ? event.message : 'processing failed'
      });
      return;
    }

    this.#registry.emit(jobId, { stage: event.stage as Stage });
  }
}
