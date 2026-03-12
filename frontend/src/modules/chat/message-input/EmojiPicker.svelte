<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Smile } from 'lucide-svelte';

  export let emojis: string[] = [];
  export let onSelect: (emoji: string) => void;

  let isOpen = false;
  let root: HTMLDivElement | null = null;

  function toggleOpen(): void {
    isOpen = !isOpen;
  }

  function handleSelect(emoji: string): void {
    onSelect(emoji);
    isOpen = false;
  }

  function handleDocumentPointerDown(event: PointerEvent): void {
    if (!isOpen || !root) {
      return;
    }

    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }

    if (root.contains(target)) {
      return;
    }

    isOpen = false;
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });
</script>

<div class="message-input-emoji-picker" bind:this={root}>
  <button
    type="button"
    class:message-input-emoji-button-active={isOpen}
    class="message-input-emoji-button"
    aria-label="Emoji"
    on:click={toggleOpen}
  >
    <Smile class="h-5 w-5" />
  </button>
  {#if isOpen}
    <div class="message-input-emoji-panel">
      <div class="message-input-emoji-grid app-scrollbar">
        {#each emojis as emoji (emoji)}
          <button
            type="button"
            class="message-input-emoji-option"
            on:click={() => handleSelect(emoji)}
            title={emoji}
            aria-label={emoji}
          >
            {emoji}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .message-input-emoji-picker {
    @apply relative;
  }

  .message-input-emoji-button {
    @apply flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-300 transition hover:bg-white/10 hover:text-slate-100;
  }

  .message-input-emoji-button-active {
    @apply bg-white/10 text-slate-100;
  }

  .message-input-emoji-panel {
    @apply absolute bottom-full right-0 z-30 mb-2 w-[280px] rounded-lg border border-white/15 bg-surface-900 p-2 shadow-lg;
  }

  .message-input-emoji-grid {
    @apply grid max-h-48 grid-cols-8 gap-1 overflow-auto pr-1;
  }

  .message-input-emoji-option {
    @apply rounded px-1.5 py-1 text-base transition hover:bg-white/10;
  }
</style>
