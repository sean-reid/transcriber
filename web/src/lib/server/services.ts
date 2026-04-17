import { readEnv } from './env';
import { jobs } from './jobs';
import { LocalStorage, type Storage } from './storage';
import { LocalWorker, type Worker } from './worker';

let cached: { storage: Storage; worker: Worker } | undefined;

export function services(platform: App.Platform | undefined): {
  storage: Storage;
  worker: Worker;
} {
  if (cached) return cached;

  const env = readEnv(platform);
  if (env.storageDriver === 'r2') {
    throw new Error('r2 storage driver not wired yet; set STORAGE_DRIVER=local for now');
  }
  const storage = new LocalStorage(env.localStorageRoot);

  if (env.workerDriver === 'remote') {
    throw new Error('remote worker driver not wired yet; set WORKER_DRIVER=local for now');
  }
  const worker = new LocalWorker(storage, jobs());

  cached = { storage, worker };
  return cached;
}
