<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import Metronome from '$lib/components/Metronome.svelte';
  import { renderQrSvg } from '$lib/client/qr';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  let shareUrl = $state('');
  let qrSvg = $state<string>('');
  let showQr = $state(false);
  let copied = $state(false);
  let remainingLabel = $state('');
  let tick: ReturnType<typeof setInterval> | undefined;
  let copiedTimer: ReturnType<typeof setTimeout> | undefined;

  function formatRemaining(ms: number): string {
    const secs = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    if (h > 0) return `${h}h ${m.toString().padStart(2, '0')}m`;
    const s = secs % 60;
    return `${m}m ${s.toString().padStart(2, '0')}s`;
  }

  onMount(() => {
    shareUrl = window.location.href;
    tick = setInterval(() => {
      remainingLabel = formatRemaining(data.expiresAt - Date.now());
    }, 1000);
    remainingLabel = formatRemaining(data.expiresAt - Date.now());
  });

  onDestroy(() => {
    if (tick) clearInterval(tick);
    if (copiedTimer) clearTimeout(copiedTimer);
  });

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      copied = true;
      copiedTimer = setTimeout(() => {
        copied = false;
      }, 1800);
    } catch {
      copied = false;
    }
  }

  async function toggleQr() {
    showQr = !showQr;
    if (showQr && !qrSvg && shareUrl) {
      qrSvg = await renderQrSvg(shareUrl);
    }
  }
</script>

<main>
  <header>
    <a href="/" class="wordmark">
      <span class="mono">transcriber</span>
      <Metronome bpm={60} active={false} />
    </a>
    <span class="expiry mono" title="Automatic deletion">
      {#if remainingLabel}expires in {remainingLabel}{/if}
    </span>
  </header>

  <section class="stage">
    <div class="frame">
      <video controls playsinline preload="auto">
        <source src={data.downloadUrl} type="video/mp4" />
      </video>
    </div>
  </section>

  <section class="actions">
    <a class="primary" href={data.downloadUrl} download>
      <span>Download mp4</span>
    </a>
    <div class="secondary">
      <button type="button" class="ghost" onclick={copyLink}>
        {copied ? 'link copied' : 'copy link'}
      </button>
      <button type="button" class="ghost" onclick={toggleQr} aria-expanded={showQr}>
        {showQr ? 'hide qr' : 'show qr'}
      </button>
    </div>
  </section>

  {#if showQr}
    <section class="qr" aria-label="Share via QR code">
      {#if qrSvg}
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        <div class="qr-svg">{@html qrSvg}</div>
        <p class="qr-caption mono">point a camera to open</p>
      {/if}
    </section>
  {/if}

  <p class="hint mono">one-time link · delete from your device if you want to keep it private</p>
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
    padding: var(--space-4) 0 var(--space-8);
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

  .expiry {
    color: var(--ink-muted);
    font-size: var(--step--1);
  }

  .stage {
    display: flex;
    justify-content: center;
    padding-bottom: var(--space-5);
  }

  .frame {
    position: relative;
    max-width: 520px;
    width: 100%;
    border: 1px solid var(--rule);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: #000;
  }

  video {
    display: block;
    width: 100%;
    height: auto;
    max-height: 80vh;
    object-fit: contain;
    background: #000;
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    align-items: center;
    padding: var(--space-4) 0 var(--space-5);
  }

  .primary {
    display: inline-block;
    background: var(--ink);
    color: var(--paper);
    padding: 14px 24px;
    border-radius: 999px;
    font-family: var(--font-sans);
    font-size: var(--step-0);
    font-variation-settings: 'wght' 500;
    text-decoration: none;
    transition:
      transform 140ms var(--ease-out),
      box-shadow 200ms var(--ease-out),
      background 140ms var(--ease-out);
  }

  .primary:hover {
    background: var(--accent-ink);
    transform: translateY(-1px);
    box-shadow: 0 4px 0 rgba(17, 17, 17, 0.08);
  }

  .secondary {
    display: inline-flex;
    gap: var(--space-3);
    align-items: center;
  }

  .ghost {
    background: transparent;
    border: 1px solid var(--rule);
    padding: 8px 14px;
    border-radius: 999px;
    font-family: var(--font-mono);
    font-size: var(--step--1);
    color: var(--ink);
    transition:
      border-color 140ms var(--ease-out),
      box-shadow 200ms var(--ease-out);
  }

  .ghost:hover {
    border-color: var(--ink);
    box-shadow: 0 0 0 4px rgba(190, 58, 31, 0.08);
  }

  .qr {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    padding-bottom: var(--space-6);
  }

  .qr-svg {
    width: 240px;
    height: 240px;
    background: var(--paper-raised);
    padding: var(--space-3);
    border: 1px solid var(--rule);
    border-radius: var(--radius-md);
  }

  .qr-caption {
    color: var(--ink-soft);
    font-size: var(--step--2);
  }

  .hint {
    margin-top: auto;
    padding-top: var(--space-7);
    text-align: center;
    color: var(--ink-soft);
    font-size: var(--step--2);
    border-top: 1px solid var(--rule);
  }

  @media (min-width: 900px) {
    .stage {
      padding-bottom: var(--space-4);
    }
    .actions {
      flex-direction: row;
      justify-content: center;
      gap: var(--space-4);
    }
  }
</style>
