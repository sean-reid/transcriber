<script lang="ts">
  type Props = { hover?: boolean; busy?: boolean };
  let { hover = false, busy = false }: Props = $props();
</script>

<div class="wrap" class:hover class:busy aria-hidden="true">
  <svg viewBox="0 0 1000 180" preserveAspectRatio="xMidYMid meet" class="staff">
    <g stroke="currentColor" stroke-width="1" fill="none" vector-effect="non-scaling-stroke">
      <line x1="40" x2="960" y1="60" y2="60" />
      <line x1="40" x2="960" y1="80" y2="80" />
      <line x1="40" x2="960" y1="100" y2="100" />
      <line x1="40" x2="960" y1="120" y2="120" />
      <line x1="40" x2="960" y1="140" y2="140" />
    </g>

    <line x1="40" y1="60" x2="40" y2="140" stroke="currentColor" stroke-width="1.5" />
    <line x1="955" y1="60" x2="955" y2="140" stroke="currentColor" stroke-width="1.5" />
    <line x1="960" y1="60" x2="960" y2="140" stroke="currentColor" stroke-width="2.4" />

    <text
      x="52"
      y="132"
      font-family="serif"
      font-size="108"
      fill="currentColor"
      class="clef"
      aria-hidden="true"
    >
      &#x1D11E;
    </text>

    <g class="time-sig">
      <text
        x="152"
        y="98"
        font-family="var(--font-display)"
        font-size="42"
        font-weight="700"
        fill="currentColor"
        text-anchor="middle">4</text
      >
      <text
        x="152"
        y="136"
        font-family="var(--font-display)"
        font-size="42"
        font-weight="700"
        fill="currentColor"
        text-anchor="middle">4</text
      >
    </g>

    <line
      x1="210"
      y1="60"
      x2="210"
      y2="140"
      stroke="currentColor"
      stroke-width="0.75"
      opacity="0.4"
    />
    <line
      x1="395"
      y1="60"
      x2="395"
      y2="140"
      stroke="currentColor"
      stroke-width="0.75"
      opacity="0.4"
    />
    <line
      x1="580"
      y1="60"
      x2="580"
      y2="140"
      stroke="currentColor"
      stroke-width="0.75"
      opacity="0.4"
    />
    <line
      x1="765"
      y1="60"
      x2="765"
      y2="140"
      stroke="currentColor"
      stroke-width="0.75"
      opacity="0.4"
    />

    <rect x="490" y="80" width="36" height="10" fill="currentColor" class="rest" />

    <line
      x1="500"
      y1="50"
      x2="500"
      y2="150"
      stroke="var(--accent)"
      stroke-width="1.2"
      class="playhead"
      class:hover
    />
  </svg>
</div>

<style>
  .wrap {
    width: 100%;
    color: var(--ink);
    transition: color 180ms var(--ease-out);
  }

  .wrap.hover {
    color: var(--ink);
  }

  .staff {
    width: 100%;
    height: auto;
    display: block;
  }

  .rest {
    transition: opacity 180ms var(--ease-out);
  }

  .wrap.hover .rest {
    opacity: 0.25;
  }

  .wrap.busy .rest {
    opacity: 0;
  }

  .playhead {
    opacity: 0;
    transition: opacity 180ms var(--ease-out);
  }

  .wrap.hover .playhead {
    opacity: 0.85;
    animation: metronome 1s var(--ease-in-out) infinite alternate;
  }

  .wrap.busy .playhead {
    opacity: 0.85;
    animation: sweep 4s var(--ease-out) infinite;
  }

  @keyframes metronome {
    from {
      transform: translateX(-6px);
    }
    to {
      transform: translateX(6px);
    }
  }

  @keyframes sweep {
    0% {
      transform: translateX(-460px);
    }
    100% {
      transform: translateX(460px);
    }
  }

  .clef {
    font-family: 'Fraunces Variable', 'Iowan Old Style', Georgia, serif;
    font-variation-settings: 'opsz' 144;
  }
</style>
