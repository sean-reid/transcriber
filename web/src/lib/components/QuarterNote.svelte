<script lang="ts">
  type Props = { size?: number; filled?: boolean };
  let { size = 36, filled = true }: Props = $props();
</script>

<svg
  width={size}
  height={size * 2}
  viewBox="0 0 40 80"
  role="img"
  aria-label="Quarter note"
  class="note"
>
  <ellipse
    cx="14"
    cy="60"
    rx="12"
    ry="8"
    fill={filled ? 'currentColor' : 'none'}
    stroke="currentColor"
    stroke-width={filled ? 0 : 2}
    transform="rotate(-20 14 60)"
  />
  <line x1="24" y1="58" x2="24" y2="6" stroke="currentColor" stroke-width="2" />
</svg>

<style>
  .note {
    display: inline-block;
    color: var(--ink);
    vertical-align: middle;
  }
</style>
