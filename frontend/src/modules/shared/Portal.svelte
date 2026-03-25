<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  let host: HTMLDivElement | null = null;
  let portalTarget: HTMLElement | null = null;

  onMount(() => {
    portalTarget = document.body;
    if (host && portalTarget) {
      portalTarget.appendChild(host);
    }
  });

  onDestroy(() => {
    host?.remove();
    portalTarget = null;
  });
</script>

<div bind:this={host} class="portal-host">
  <slot />
</div>

<style>
  .portal-host {
    display: contents;
  }
</style>
