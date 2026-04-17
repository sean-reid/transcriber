import { createReadStream, createWriteStream } from 'node:fs';
import { mkdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { dirname, join, resolve, sep } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import type { ReadableStream as NodeReadableStream } from 'node:stream/web';

export type StorageObject = {
  stream: ReadableStream<Uint8Array>;
  size: number;
  contentType: string;
};

export interface Storage {
  put(key: string, body: ReadableStream<Uint8Array>, contentType: string): Promise<void>;
  get(key: string): Promise<StorageObject | null>;
  exists(key: string): Promise<boolean>;
  delete(key: string): Promise<void>;
  publicUrl(key: string, ttlSeconds: number): Promise<string>;
}

const DEFAULT_CONTENT_TYPE = 'application/octet-stream';
const META_SUFFIX = '.meta.json';

export class LocalStorage implements Storage {
  readonly #root: string;
  readonly #baseUrl: string;

  constructor(root: string, baseUrl = '/api/storage') {
    this.#root = resolve(root);
    this.#baseUrl = baseUrl;
  }

  localPath(key: string): string {
    const full = resolve(join(this.#root, key));
    if (full !== this.#root && !full.startsWith(this.#root + sep)) {
      throw new Error(`invalid key: ${key}`);
    }
    return full;
  }

  async put(key: string, body: ReadableStream<Uint8Array>, contentType: string): Promise<void> {
    const path = this.localPath(key);
    await mkdir(dirname(path), { recursive: true });
    await pipeline(
      Readable.fromWeb(body as NodeReadableStream<Uint8Array>),
      createWriteStream(path)
    );
    await writeFile(path + META_SUFFIX, JSON.stringify({ contentType }), 'utf8');
  }

  async get(key: string): Promise<StorageObject | null> {
    const path = this.localPath(key);
    let size: number;
    try {
      const s = await stat(path);
      size = s.size;
    } catch {
      return null;
    }
    const contentType = await this.#readContentType(path);
    const web = Readable.toWeb(createReadStream(path)) as unknown as ReadableStream<Uint8Array>;
    return { stream: web, size, contentType };
  }

  async exists(key: string): Promise<boolean> {
    try {
      await stat(this.localPath(key));
      return true;
    } catch {
      return false;
    }
  }

  async delete(key: string): Promise<void> {
    const path = this.localPath(key);
    await Promise.all([rm(path, { force: true }), rm(path + META_SUFFIX, { force: true })]);
  }

  async publicUrl(key: string, _ttlSeconds: number): Promise<string> {
    return `${this.#baseUrl}/${encodeURI(key)}`;
  }

  async #readContentType(path: string): Promise<string> {
    try {
      const raw = await readFile(path + META_SUFFIX, 'utf8');
      const meta = JSON.parse(raw) as { contentType?: string };
      return meta.contentType ?? DEFAULT_CONTENT_TYPE;
    } catch {
      return DEFAULT_CONTENT_TYPE;
    }
  }
}
