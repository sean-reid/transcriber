export type Stage =
  | 'queued'
  | 'uploading'
  | 'extracting'
  | 'detecting'
  | 'rendering'
  | 'encoding'
  | 'done'
  | 'failed';

export const STAGES: readonly Stage[] = [
  'queued',
  'extracting',
  'detecting',
  'rendering',
  'encoding',
  'done'
] as const;

export type JobEvent = {
  stage: Stage;
  at: number;
  message?: string;
  outputKey?: string;
};

export type Job = {
  id: string;
  inputKey: string;
  createdAt: number;
  expiresAt: number;
  events: JobEvent[];
  subscribers: Set<(event: JobEvent) => void>;
};

export interface JobRegistry {
  create(id: string, inputKey: string, ttlSeconds: number): Job;
  get(id: string): Job | undefined;
  emit(id: string, event: Omit<JobEvent, 'at'>): void;
  subscribe(id: string, handler: (event: JobEvent) => void): () => void;
  latest(id: string): JobEvent | undefined;
}

class MemoryJobRegistry implements JobRegistry {
  private jobs = new Map<string, Job>();

  create(id: string, inputKey: string, ttlSeconds: number): Job {
    const now = Date.now();
    const job: Job = {
      id,
      inputKey,
      createdAt: now,
      expiresAt: now + ttlSeconds * 1000,
      events: [{ stage: 'queued', at: now }],
      subscribers: new Set()
    };
    this.jobs.set(id, job);
    return job;
  }

  get(id: string): Job | undefined {
    return this.jobs.get(id);
  }

  emit(id: string, event: Omit<JobEvent, 'at'>): void {
    const job = this.jobs.get(id);
    if (!job) return;
    const full: JobEvent = { ...event, at: Date.now() };
    job.events.push(full);
    for (const sub of job.subscribers) {
      try {
        sub(full);
      } catch {
        // ignore subscriber errors
      }
    }
  }

  subscribe(id: string, handler: (event: JobEvent) => void): () => void {
    const job = this.jobs.get(id);
    if (!job) throw new Error(`unknown job ${id}`);
    job.subscribers.add(handler);
    return () => {
      job.subscribers.delete(handler);
    };
  }

  latest(id: string): JobEvent | undefined {
    const job = this.jobs.get(id);
    return job?.events.at(-1);
  }
}

let instance: JobRegistry | undefined;

export function jobs(): JobRegistry {
  if (!instance) {
    instance = new MemoryJobRegistry();
  }
  return instance;
}
