<script lang="ts">
  import { goto } from '$app/navigation';
  import DropStaff from '$lib/components/DropStaff.svelte';
  import Metronome from '$lib/components/Metronome.svelte';
  import { readVideoDuration } from '$lib/client/duration';
  import { uploadVideo } from '$lib/client/upload';
  import { MAX_DURATION_SECONDS, MAX_FILE_BYTES, ACCEPTED_MIME } from '$lib/shared/config';

  let dragActive = $state(false);
  let busy = $state(false);
  let errorText = $state<string | null>(null);

  async function handle(file: File) {
    errorText = null;
    if (!ACCEPTED_MIME.includes(file.type)) {
      errorText = 'Unsupported format. Try MP4, MOV, WebM, or MKV.';
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      errorText = 'That file is too large.';
      return;
    }
    busy = true;
    try {
      const duration = await readVideoDuration(file);
      if (duration > MAX_DURATION_SECONDS + 0.25) {
        errorText = `Keep it under ${MAX_DURATION_SECONDS} seconds.`;
        busy = false;
        return;
      }
      const { jobId } = await uploadVideo(file);
      await goto(`/jobs/${jobId}`);
    } catch (err) {
      errorText = err instanceof Error ? err.message : 'Upload failed.';
      busy = false;
    }
  }

  function onFileChange(ev: Event) {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (file) void handle(file);
  }

  function onDrop(ev: DragEvent) {
    ev.preventDefault();
    dragActive = false;
    const file = ev.dataTransfer?.files?.[0];
    if (file) void handle(file);
  }

  function onDragOver(ev: DragEvent) {
    ev.preventDefault();
    if (!dragActive) dragActive = true;
  }

  function onDragLeave(ev: DragEvent) {
    if (ev.currentTarget === ev.target) dragActive = false;
  }
</script>

<main>
  <header>
    <span class="wordmark">
      <span class="mono">transcriber</span>
      <Metronome bpm={60} />
    </span>
  </header>

  <label
    class="drop"
    class:drag={dragActive}
    class:busy
    ondrop={onDrop}
    ondragover={onDragOver}
    ondragleave={onDragLeave}
  >
    <input
      id="file-upload"
      type="file"
      accept={ACCEPTED_MIME.join(',')}
      class="sr-only"
      onchange={onFileChange}
    />
    <DropStaff hover={dragActive} busy={!!busy} />
    <span class="drop-label">
      {#if busy}
        <span class="mono">uploading</span>
      {:else if dragActive}
        <span class="mono">release</span>
      {:else}
        <span class="mono">drop a clip, or click to choose one</span>
      {/if}
    </span>
  </label>

  <div class="meta">
    <span class="mono">mp4 &middot; mov &middot; webm &middot; up to 30 seconds</span>
    <label class="link">
      <input
        type="file"
        accept="video/*"
        capture="environment"
        class="sr-only"
        onchange={onFileChange}
      />
      record with camera
    </label>
  </div>

  {#if errorText}
    <p class="error" role="alert">{errorText}</p>
  {/if}

  <footer>
    <span class="mono">links expire after 24 hours</span>
  </footer>
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
  }

  .drop {
    position: relative;
    display: block;
    padding: 0 0 var(--space-2);
    cursor: pointer;
    user-select: none;
  }

  .drop-label {
    display: block;
    text-align: center;
    color: var(--ink-soft);
    font-size: var(--step--1);
    padding-top: var(--space-5);
    letter-spacing: 0.01em;
  }

  .drop.drag .drop-label {
    color: var(--accent);
  }

  .drop.busy {
    cursor: progress;
  }

  .drop:focus-within {
    outline: none;
  }

  .drop:focus-within .drop-label {
    color: var(--ink);
  }

  .meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: var(--space-3);
    padding: var(--space-5) 0 0;
    color: var(--ink-soft);
    font-size: var(--step--1);
  }

  .link {
    display: inline-block;
    padding: 0;
    color: var(--ink);
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--step--1);
    text-underline-offset: 3px;
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-decoration-color: var(--rule);
    transition: text-decoration-color 140ms var(--ease-out);
  }

  .link:hover {
    text-decoration-color: var(--accent);
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .error {
    color: var(--accent);
    font-size: var(--step--1);
    font-family: var(--font-mono);
    margin-top: var(--space-4);
  }

  footer {
    margin-top: auto;
    padding-top: var(--space-9);
    color: var(--ink-soft);
    font-size: var(--step--2);
  }

  @media (max-width: 560px) {
    header {
      padding-bottom: var(--space-7);
    }
    .meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--space-2);
    }
  }
</style>
