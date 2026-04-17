import { AwsClient } from 'aws4fetch';
import type { Storage, StorageObject, StorageRange } from './storage';

const SERVICE = 's3';

export type R2Config = {
  accountId: string;
  accessKeyId: string;
  secretAccessKey: string;
  bucket: string;
};

export class R2Storage implements Storage {
  readonly #client: AwsClient;
  readonly #endpoint: string;
  readonly #bucket: string;

  constructor(config: R2Config) {
    this.#client = new AwsClient({
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey,
      service: SERVICE,
      region: 'auto'
    });
    this.#endpoint = `https://${config.accountId}.r2.cloudflarestorage.com`;
    this.#bucket = config.bucket;
  }

  #objectUrl(key: string): string {
    const encoded = key
      .split('/')
      .map((segment) => encodeURIComponent(segment))
      .join('/');
    return `${this.#endpoint}/${this.#bucket}/${encoded}`;
  }

  async put(key: string, body: ReadableStream<Uint8Array>, contentType: string): Promise<void> {
    const buffer = await new Response(body).arrayBuffer();
    const response = await this.#client.fetch(this.#objectUrl(key), {
      method: 'PUT',
      headers: { 'content-type': contentType, 'content-length': String(buffer.byteLength) },
      body: buffer
    });
    if (!response.ok) {
      throw new Error(`r2 put failed: ${response.status} ${await response.text()}`);
    }
  }

  async get(key: string, range?: StorageRange): Promise<StorageObject | null> {
    const headers: Record<string, string> = {};
    if (range) {
      headers['range'] = `bytes=${range.start}-${range.end}`;
    }
    const response = await this.#client.fetch(this.#objectUrl(key), { headers });
    if (response.status === 404) return null;
    if (!response.ok && response.status !== 206) {
      throw new Error(`r2 get failed: ${response.status}`);
    }
    const contentType = response.headers.get('content-type') ?? 'application/octet-stream';
    const size = Number(response.headers.get('content-length') ?? 0);
    const stream = response.body as ReadableStream<Uint8Array> | null;
    if (!stream) return null;
    return { stream, size, contentType };
  }

  async size(key: string): Promise<number | null> {
    const response = await this.#client.fetch(this.#objectUrl(key), { method: 'HEAD' });
    if (response.status === 404) return null;
    if (!response.ok) return null;
    const len = response.headers.get('content-length');
    return len ? Number(len) : null;
  }

  async exists(key: string): Promise<boolean> {
    return (await this.size(key)) !== null;
  }

  async delete(key: string): Promise<void> {
    await this.#client.fetch(this.#objectUrl(key), { method: 'DELETE' });
  }

  async publicUrl(key: string, ttlSeconds: number): Promise<string> {
    const signed = await this.#client.sign(this.#objectUrl(key), {
      method: 'GET',
      aws: { signQuery: true, allHeaders: false, service: SERVICE },
      headers: {}
    });
    const url = new URL(signed.url);
    url.searchParams.set('X-Amz-Expires', String(ttlSeconds));
    return url.toString();
  }
}
