<script lang="ts">
  type Props = {
    width?: number;
    height?: number;
    spacing?: number;
    clef?: 'treble' | 'bass' | 'none';
    glyphs?: { x: number; pitch: number; kind?: 'filled' | 'open' | 'rest' }[];
    animate?: boolean;
  };

  let {
    width = 640,
    height = 120,
    spacing = 12,
    clef = 'treble',
    glyphs = [],
    animate = false
  }: Props = $props();

  const lineY = (i: number) => height / 2 - spacing * 2 + i * spacing;
  const pitchY = (pitch: number) => height / 2 + pitch * (spacing / 2);
</script>

<svg
  viewBox="0 0 {width} {height}"
  {width}
  {height}
  class="staff"
  class:animate
  role="img"
  aria-label="Music staff"
  preserveAspectRatio="xMidYMid meet"
>
  <g class="lines" stroke="currentColor" stroke-width="1" vector-effect="non-scaling-stroke">
    {#each [0, 1, 2, 3, 4] as i (i)}
      <line x1="0" x2={width} y1={lineY(i)} y2={lineY(i)} />
    {/each}
  </g>

  {#if clef === 'treble'}
    <text
      x="16"
      y={lineY(3) + 16}
      font-family="serif"
      font-size={spacing * 5.6}
      fill="currentColor"
      class="clef">&#x1D11E;</text
    >
  {:else if clef === 'bass'}
    <text
      x="16"
      y={lineY(1) + 6}
      font-family="serif"
      font-size={spacing * 4.2}
      fill="currentColor"
      class="clef">&#x1D122;</text
    >
  {/if}

  <g class="glyphs">
    {#each glyphs as g, idx (idx)}
      {#if g.kind === 'rest'}
        <rect
          x={g.x - spacing * 0.6}
          y={lineY(1) - spacing * 0.2}
          width={spacing * 1.2}
          height={spacing * 0.6}
          fill="currentColor"
        />
      {:else}
        <ellipse
          cx={g.x}
          cy={pitchY(g.pitch)}
          rx={spacing * 0.55}
          ry={spacing * 0.38}
          fill={g.kind === 'open' ? 'none' : 'currentColor'}
          stroke="currentColor"
          stroke-width={g.kind === 'open' ? 1.2 : 0}
          transform="rotate(-18 {g.x} {pitchY(g.pitch)})"
        />
        <line
          x1={g.x + spacing * 0.5}
          x2={g.x + spacing * 0.5}
          y1={pitchY(g.pitch)}
          y2={pitchY(g.pitch) - spacing * 3.2}
          stroke="currentColor"
          stroke-width="1.1"
        />
      {/if}
    {/each}
  </g>
</svg>

<style>
  .staff {
    color: var(--ink);
    display: block;
  }

  .lines line {
    opacity: 0.85;
  }

  .clef {
    user-select: none;
  }

  .animate .glyphs {
    animation: notes-in 600ms var(--ease-out) both;
  }

  @keyframes notes-in {
    from {
      opacity: 0;
      transform: translateX(12px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }
</style>
