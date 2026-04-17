<script lang="ts">
  import '../app.css';
  let { children } = $props();
</script>

<svelte:head>
  <title>transcriber</title>
  <meta name="description" content="Turn a short video into a clip with staff notation." />
</svelte:head>

{@render children()}
