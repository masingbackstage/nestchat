<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Pencil, Plus, Trash2 } from 'lucide-svelte';
  import type { CustomEmojiOption } from './utils';

  export let canManage = false;
  export let canReact = true;
  export let isBusy = false;
  export let isDeleted = false;
  export let isPending = false;
  export let isEditing = false;
  export let isVisible = false;
  export let customEmojis: CustomEmojiOption[] = [];
  export let unicodeEmojis: string[] = [];
  export let onEdit: () => void;
  export let onDelete: () => void;
  export let onToggleReaction: (emoji: string) => void;

  let isOpen = false;
  let search = '';
  let root: HTMLDivElement | null = null;

  $: normalizedSearch = search.trim().toLowerCase();
  $: filteredCustomEmojis =
    normalizedSearch.length === 0
      ? customEmojis
      : customEmojis.filter(
          (item) =>
            item.label.toLowerCase().includes(normalizedSearch) ||
            item.token.toLowerCase().includes(normalizedSearch),
        );
  $: filteredUnicodeEmojis =
    normalizedSearch.length === 0
      ? unicodeEmojis
      : unicodeEmojis.filter((emoji) => emoji.includes(normalizedSearch));

  function closePicker(): void {
    isOpen = false;
    search = '';
  }

  function togglePicker(): void {
    isOpen = !isOpen;
    if (!isOpen) {
      search = '';
    }
  }

  function handleSelectReaction(emoji: string): void {
    onToggleReaction(emoji);
    closePicker();
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

    closePicker();
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });
</script>

{#if (canManage || canReact) && !isPending && !isEditing}
  <div
    bind:this={root}
    class:reaction-picker-toolbar-open={isOpen}
    class:reaction-picker-toolbar-visible={isVisible}
    class="reaction-picker-toolbar"
  >
    {#if !isDeleted}
      {#if canReact}
        <button
          type="button"
          class="reaction-picker-icon-button"
          on:click={togglePicker}
          disabled={isBusy || isPending}
          aria-label="Add reaction"
          title="Add reaction"
        >
          <Plus class="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      {/if}
      <button
        type="button"
        class="reaction-picker-icon-button"
        on:click={onEdit}
        disabled={isBusy}
        aria-label="Edit message"
        title="Edit"
      >
        <Pencil class="h-3.5 w-3.5" aria-hidden="true" />
      </button>
      <button
        type="button"
        class="reaction-picker-icon-button reaction-picker-icon-button-danger"
        on:click={onDelete}
        disabled={isBusy}
        aria-label="Delete message"
        title="Delete"
      >
        <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    {/if}

    {#if isOpen}
      <div class="reaction-picker-panel">
        <input
          type="text"
          bind:value={search}
          placeholder="Search emoji..."
          class="reaction-picker-search"
        />

        {#if filteredCustomEmojis.length > 0}
          <p class="reaction-picker-label">Server emojis</p>
          <div class="reaction-picker-grid reaction-picker-grid-custom app-scrollbar">
            {#each filteredCustomEmojis as item (item.token)}
              <button
                type="button"
                class="reaction-picker-custom-button"
                on:click={() => handleSelectReaction(item.token)}
                title={`:${item.label}:`}
                aria-label={`:${item.label}:`}
                disabled={isBusy || isPending}
              >
                {#if item.imageUrl}
                  <img src={item.imageUrl} alt={item.label} class="reaction-picker-custom-image" />
                {:else}
                  <span class="reaction-picker-custom-fallback">:{item.label}:</span>
                {/if}
              </button>
            {/each}
          </div>
        {/if}

        <p class="reaction-picker-label">Emoji</p>
        <div class="reaction-picker-grid app-scrollbar">
          {#each filteredUnicodeEmojis as emoji (emoji)}
            <button
              type="button"
              class="reaction-picker-unicode-button"
              on:click={() => handleSelectReaction(emoji)}
              title={emoji}
              aria-label={emoji}
              disabled={isBusy || isPending}
            >
              {emoji}
            </button>
          {/each}
        </div>
        {#if filteredCustomEmojis.length === 0 && filteredUnicodeEmojis.length === 0}
          <p class="reaction-picker-empty">No emoji found.</p>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .reaction-picker-toolbar {
    @apply pointer-events-none absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg border border-white/10 bg-surface-900/95 p-0.5 opacity-0 shadow-lg transition-opacity;
  }

  .reaction-picker-toolbar-open {
    @apply pointer-events-auto opacity-100;
  }

  .reaction-picker-toolbar-visible {
    @apply pointer-events-auto opacity-100;
  }

  .reaction-picker-icon-button {
    @apply rounded-md p-1 text-muted-300 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-50;
  }

  .reaction-picker-icon-button-danger {
    @apply text-red-300 hover:bg-red-500/15 hover:text-red-200;
  }

  .reaction-picker-panel {
    @apply absolute right-0 top-full z-20 mt-1 w-[280px] rounded-lg border border-white/15 bg-surface-900 p-2 shadow-lg;
  }

  .reaction-picker-search {
    @apply mb-2 w-full rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-slate-100 outline-none placeholder:text-muted-500 focus:border-accent-400;
  }

  .reaction-picker-label {
    @apply mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-400;
  }

  .reaction-picker-grid {
    @apply grid max-h-40 grid-cols-8 gap-1 overflow-auto pr-1;
  }

  .reaction-picker-grid-custom {
    @apply mb-2 max-h-24;
  }

  .reaction-picker-custom-button {
    @apply flex h-8 w-8 items-center justify-center rounded transition hover:bg-white/10;
  }

  .reaction-picker-custom-image {
    @apply h-6 w-6 object-contain;
  }

  .reaction-picker-custom-fallback {
    @apply text-xs text-muted-300;
  }

  .reaction-picker-unicode-button {
    @apply rounded px-1.5 py-1 text-base transition hover:bg-white/10;
  }

  .reaction-picker-empty {
    @apply mt-2 text-center text-xs text-muted-400;
  }
</style>
