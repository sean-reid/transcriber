type Env = {
  storageDriver: 'local' | 'r2';
  localStorageRoot: string;
  r2AccountId?: string;
  r2AccessKeyId?: string;
  r2SecretAccessKey?: string;
  r2Bucket?: string;
  workerDriver: 'local' | 'remote';
  workerUrl?: string;
  jobTtlSeconds: number;
};

export function readEnv(platform: App.Platform | undefined): Env {
  const cf = platform?.env ?? ({} as Record<string, string | undefined>);
  const fromProc = typeof process !== 'undefined' ? process.env : {};

  const pick = (k: string): string | undefined =>
    (cf as Record<string, string | undefined>)[k] ?? fromProc[k];

  const driver = (pick('STORAGE_DRIVER') ?? 'local') as 'local' | 'r2';
  const workerDriver = (pick('WORKER_DRIVER') ?? 'local') as 'local' | 'remote';

  return {
    storageDriver: driver === 'r2' ? 'r2' : 'local',
    localStorageRoot: pick('LOCAL_STORAGE_ROOT') ?? '/tmp/transcriber',
    r2AccountId: pick('R2_ACCOUNT_ID'),
    r2AccessKeyId: pick('R2_ACCESS_KEY_ID'),
    r2SecretAccessKey: pick('R2_SECRET_ACCESS_KEY'),
    r2Bucket: pick('R2_BUCKET'),
    workerDriver: workerDriver === 'remote' ? 'remote' : 'local',
    workerUrl: pick('WORKER_URL'),
    jobTtlSeconds: Number(pick('JOB_TTL_SECONDS') ?? 86400)
  };
}
