<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import DropStaff from '$lib/components/DropStaff.svelte';
  import Metronome from '$lib/components/Metronome.svelte';
  import type { PageData } from './$types';

  type Stage = 'queued' | 'extracting' | 'detecting' | 'rendering' | 'encoding' | 'done' | 'failed';

  type StageEvent = { stage: Stage; at: number; message?: string; outputKey?: string };

  let { data }: { data: PageData } = $props();

  const pipeline: { key: Exclude<Stage, 'queued' | 'failed'>; label: string }[] = [
    { key: 'extracting', label: 'extracting audio' },
    { key: 'detecting', label: 'detecting notes' },
    { key: 'rendering', label: 'engraving measures' },
    { key: 'encoding', label: 'encoding mp4' },
    { key: 'done', label: 'finished' }
  ];

  let stage: Stage = $state('queued');
  const startedAt = Date.now();
  let elapsed = $state(0);
  let failed: string | null = $state(null);
  let source: EventSource | null = null;
  let tick: ReturnType<typeof setInterval> | undefined;

  const currentIndex = $derived(pipeline.findIndex((p) => p.key === stage));
  const stageLabel = $derived(
    stage === 'queued'
      ? 'queued'
      : stage === 'failed'
        ? 'failed'
        : (pipeline.find((p) => p.key === stage)?.label ?? stage)
  );

  function format(s: number): string {
    const sec = Math.max(0, Math.floor(s / 1000));
    const m = Math.floor(sec / 60);
    const r = sec % 60;
    return `${m.toString().padStart(2, '0')}:${r.toString().padStart(2, '0')}`;
  }

  onMount(() => {
    stage = data.stage as Stage;
    source = new EventSource(`/api/jobs/${data.id}/events`);
    source.addEventListener('message', (e) => {
      const ev = JSON.parse(e.data) as StageEvent;
      stage = ev.stage;
      if (ev.stage === 'failed') {
        failed = ev.message ?? 'processing failed';
      }
      if (ev.stage === 'done') {
        void goto(`/share/${data.id}`);
      }
    });
    source.addEventListener('error', () => {
      source?.close();
    });
    tick = setInterval(() => {
      elapsed = Date.now() - startedAt;
    }, 250);
  });

  onDestroy(() => {
    source?.close();
    if (tick) clearInterval(tick);
  });
</script>

<main>
  <header>
    <a href="/" class="wordmark">
      <span class="mono">transcriber</span>
      <Metronome bpm={60} active={!failed && stage !== 'done'} />
    </a>
    <span class="status">
      <span class="mono">{stageLabel}</span>
      <span class="sep" aria-hidden="true">·</span>
      <span class="mono clock">{format(elapsed)}</span>
    </span>
  </header>

  <section class="stage" aria-live="polite">
    <DropStaff busy={!failed && stage !== 'done'} />
  </section>

  <ol class="checklist">
    {#each pipeline as step, i (step.key)}
      {@const state =
        failed && i >= currentIndex
          ? 'failed'
          : stage === 'done' || i < currentIndex
            ? 'done'
            : i === currentIndex
              ? 'active'
              : 'pending'}
      <li class={state}>
        <span class="glyph" aria-hidden="true">
          {#if state === 'done'}&#x25A0;{:else if state === 'active'}&#x25A1;{:else if state === 'failed'}&#x2715;{:else}&#x00B7;{/if}
        </span>
        <span class="label mono">{step.label}</span>
      </li>
    {/each}
  </ol>

  {#if failed}
    <p class="error" role="alert">
      <span class="mono">{failed}</span>
      <a class="link" href="/">start over</a>
    </p>
  {/if}
</main>

<style>
  main {
    max-width: 1040px;
    margin: 0 auto;
    padding: var(--space-4) var(--space-5) var(--space-7);
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-4) 0 var(--space-9);
  }

  .wordmark {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--ink);
    font-family: var(--font-mono);
    font-variation-settings: 'wght' 500;
    font-size: var(--step--1);
    letter-spacing: 0.01em;
    text-decoration: none;
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--ink-muted);
    font-size: var(--step--1);
  }

  .status .sep {
    opacity: 0.4;
  }

  .clock {
    font-variant-numeric: tabular-nums;
    color: var(--ink);
  }

  .stage {
    padding: 0 0 var(--space-3);
  }

  .checklist {
    list-style: none;
    padding: 0;
    margin: var(--space-7) auto 0;
    max-width: 520px;
    display: grid;
    gap: var(--space-2);
  }

  .checklist li {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
    color: var(--ink-soft);
    transition: color 200ms var(--ease-out);
  }

  .checklist li.done,
  .checklist li.active {
    color: var(--ink);
  }

  .checklist li.active .label {
    color: var(--accent);
  }

  .checklist li.failed {
    color: var(--accent);
  }

  .glyph {
    width: 14px;
    display: inline-flex;
    justify-content: center;
    font-family: var(--font-mono);
    color: inherit;
  }

  .label {
    font-size: var(--step--1);
    letter-spacing: 0.01em;
  }

  .error {
    margin-top: var(--space-6);
    color: var(--accent);
    font-size: var(--step--1);
    text-align: center;
  }

  .link {
    color: var(--ink);
    text-decoration: underline;
    text-decoration-color: var(--rule);
    text-underline-offset: 3px;
    margin-left: var(--space-3);
  }

  .link:hover {
    text-decoration-color: var(--accent);
  }
</style>
