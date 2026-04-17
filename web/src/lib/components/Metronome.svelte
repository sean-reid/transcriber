<script lang="ts">
  type Props = { bpm?: number; active?: boolean };
  let { bpm = 60, active = true }: Props = $props();
  const period = $derived(`${60_000 / bpm}ms`);
</script>

<span class="dot" class:running={active} style="--period: {period}" aria-hidden="true"></span>

<style>
  .dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--ink);
    transform-origin: center;
    vertical-align: middle;
  }

  .running {
    animation: pulse var(--period) var(--ease-in-out) infinite;
  }

  @keyframes pulse {
    0%,
    100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.7);
      opacity: 0.35;
    }
  }
</style>
