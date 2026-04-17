import { readEnv } from './env';
import { jobs } from './jobs';
import { R2Storage } from './r2-storage';
import { RemoteWorker } from './remote-worker';
import { LocalStorage, type Storage } from './storage';
import { LocalWorker, type Worker } from './worker';

let cached: { storage: Storage; worker: Worker } | undefined;

export function services(platform: App.Platform | undefined): {
  storage: Storage;
  worker: Worker;
} {
  if (cached) return cached;

  const env = readEnv(platform);
  const storage = buildStorage(env);
  const worker = buildWorker(env, storage);

  cached = { storage, worker };
  return cached;
}

function buildStorage(env: ReturnType<typeof readEnv>): Storage {
  if (env.storageDriver === 'r2') {
    if (!env.r2AccountId || !env.r2AccessKeyId || !env.r2SecretAccessKey || !env.r2Bucket) {
      throw new Error(
        'STORAGE_DRIVER=r2 requires R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET'
      );
    }
    return new R2Storage({
      accountId: env.r2AccountId,
      accessKeyId: env.r2AccessKeyId,
      secretAccessKey: env.r2SecretAccessKey,
      bucket: env.r2Bucket
    });
  }
  return new LocalStorage(env.localStorageRoot);
}

function buildWorker(env: ReturnType<typeof readEnv>, storage: Storage): Worker {
  if (env.workerDriver === 'remote') {
    if (!env.workerUrl) {
      throw new Error('WORKER_DRIVER=remote requires WORKER_URL');
    }
    return new RemoteWorker(storage, jobs(), env.workerUrl);
  }
  if (!(storage instanceof LocalStorage)) {
    throw new Error('local worker driver requires local storage for file paths');
  }
  return new LocalWorker(storage, jobs());
}
