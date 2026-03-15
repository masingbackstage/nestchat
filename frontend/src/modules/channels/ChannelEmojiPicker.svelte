<script lang="ts">
  import { onDestroy } from 'svelte';
  import { UNICODE_EMOJI_PICKER } from '../../lib/emoji';

  export let value = '';
  export let disabled = false;

  let isOpen = false;
  let search = '';
  let root: HTMLDivElement | null = null;

  $: normalizedSearch = search.trim().toLowerCase();
  $: filteredEmojis =
    normalizedSearch.length === 0
      ? UNICODE_EMOJI_PICKER
      : UNICODE_EMOJI_PICKER.filter((emoji) => emoji.includes(normalizedSearch));

  function toggleOpen(): void {
    if (disabled) {
      return;
    }

    isOpen = !isOpen;
    if (!isOpen) {
      search = '';
    }
  }

  function selectEmoji(emoji: string): void {
    value = emoji;
    isOpen = false;
    search = '';
  }

  function clearValue(): void {
    value = '';
    isOpen = false;
    search = '';
  }

  function handleDocumentPointerDown(event: PointerEvent): void {
    if (!isOpen || !root) {
      return;
    }

    const target = event.target;
    if (!(target instanceof Node) || root.contains(target)) {
      return;
    }

    isOpen = false;
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });
</script>

<div class="channel-emoji-picker" bind:this={root}>
  <button
    type="button"
    class="channel-emoji-picker-trigger"
    on:click={toggleOpen}
    disabled={disabled}
  >
    <span>{value || 'Choose emoji'}</span>
    <span class="channel-emoji-picker-caret">▾</span>
  </button>

  {#if isOpen}
    <div class="channel-emoji-picker-panel">
      <input
        type="text"
        bind:value={search}
        placeholder="Search emoji..."
        class="channel-emoji-picker-search"
      />

      <div class="channel-emoji-picker-grid app-scrollbar">
        {#each filteredEmojis as emoji (emoji)}
          <button
            type="button"
            class="channel-emoji-picker-option"
            on:click={() => selectEmoji(emoji)}
            title={emoji}
            aria-label={emoji}
          >
            {emoji}
          </button>
        {/each}
      </div>

      {#if filteredEmojis.length === 0}
        <p class="channel-emoji-picker-empty">No emoji found.</p>
      {/if}

      <button
        type="button"
        class="channel-emoji-picker-clear"
        on:click={clearValue}
      >
        Clear
      </button>
    </div>
  {/if}
</div>

<style>
  .channel-emoji-picker {
    @apply relative mt-1;
  }

  .channel-emoji-picker-trigger {
    @apply flex w-full items-center justify-between rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 transition hover:border-glass-highlight disabled:cursor-not-allowed disabled:opacity-60;
  }

  .channel-emoji-picker-caret {
    @apply text-muted-400;
  }

  .channel-emoji-picker-panel {
    @apply absolute z-20 mt-1 w-full rounded-xl border border-white/15 bg-surface-900 p-2 shadow-lg;
  }

  .channel-emoji-picker-search {
    @apply mb-2 w-full rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400;
  }

  .channel-emoji-picker-grid {
    @apply mb-2 grid max-h-56 grid-cols-8 gap-1 overflow-auto pr-1;
  }

  .channel-emoji-picker-option {
    @apply rounded px-1 py-1 text-lg transition hover:bg-white/10;
  }

  .channel-emoji-picker-empty {
    @apply mb-2 text-center text-xs text-muted-400;
  }

  .channel-emoji-picker-clear {
    @apply w-full rounded border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight;
  }
</style>
