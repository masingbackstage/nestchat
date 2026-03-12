<script lang="ts">
  import { onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { fade, scale } from 'svelte/transition';
  import { UNICODE_EMOJI_PICKER } from '../../lib/emoji';

  export let isSubmitting = false;

  const dispatch = createEventDispatcher<{
    close: undefined;
    submit: {
      name: string;
      channelEmoji: string;
      channelType: 'TEXT' | 'VOICE';
      topic: string;
      isPublic: boolean;
    };
  }>();

  let name = '';
  let channelEmoji = '';
  let isEmojiPickerOpen = false;
  let emojiSearch = '';
  let channelEmojiPickerRoot: HTMLDivElement | null = null;
  let channelType: 'TEXT' | 'VOICE' = 'TEXT';
  let topic = '';
  let isPublic = true;
  $: normalizedEmojiSearch = emojiSearch.trim().toLowerCase();
  $: filteredChannelEmojis =
    normalizedEmojiSearch.length === 0
      ? UNICODE_EMOJI_PICKER
      : UNICODE_EMOJI_PICKER.filter((emoji) => emoji.includes(normalizedEmojiSearch));

  function requestClose(): void {
    if (isSubmitting) {
      return;
    }
    dispatch('close');
  }

  function handleOverlayPointerDown(event: PointerEvent): void {
    if (event.target !== event.currentTarget) {
      return;
    }
    requestClose();
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      requestClose();
    }
  }

  function submit(): void {
    if (isSubmitting || !name.trim()) {
      return;
    }

    dispatch('submit', {
      name: name.trim(),
      channelEmoji: channelEmoji.trim(),
      channelType,
      topic: topic.trim(),
      isPublic,
    });
  }

  function pickChannelEmoji(emoji: string): void {
    channelEmoji = emoji;
    isEmojiPickerOpen = false;
    emojiSearch = '';
  }

  function handleDocumentPointerDown(event: PointerEvent): void {
    if (!isEmojiPickerOpen || !channelEmojiPickerRoot) {
      return;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }
    if (channelEmojiPickerRoot.contains(target)) {
      return;
    }
    isEmojiPickerOpen = false;
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<div
  class="fixed inset-0 z-[80] flex items-center justify-center bg-surface-950/80 px-4 backdrop-blur-sm"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="glass-panel-strong w-full max-w-md rounded-[1.1rem] p-5"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <form on:submit|preventDefault={submit}>
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-slate-100">Create channel</h2>
        <button
          type="button"
          class="rounded-lg border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Close
        </button>
      </div>

      <div class="space-y-3">
        <label class="block text-sm text-muted-100">
          Name
          <input
            bind:value={name}
            type="text"
            class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
            placeholder="general"
            required
          />
        </label>

        <label class="block text-sm text-muted-100">
          Channel emoji (optional)
          <div class="relative mt-1" bind:this={channelEmojiPickerRoot}>
            <button
              type="button"
              class="flex w-full items-center justify-between rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 transition hover:border-glass-highlight"
              on:click={() => {
                isEmojiPickerOpen = !isEmojiPickerOpen;
                if (!isEmojiPickerOpen) {
                  emojiSearch = '';
                }
              }}
            >
              <span>{channelEmoji || 'Choose emoji'}</span>
              <span class="text-muted-400">▾</span>
            </button>
            {#if isEmojiPickerOpen}
              <div
                class="absolute z-20 mt-1 w-full rounded-xl border border-white/15 bg-surface-900 p-2 shadow-lg"
              >
                <input
                  type="text"
                  bind:value={emojiSearch}
                  placeholder="Search emoji..."
                  class="mb-2 w-full rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-slate-100 outline-none placeholder:text-muted-500 focus:border-accent-400"
                />
                <div class="app-scrollbar mb-2 grid max-h-56 grid-cols-8 gap-1 overflow-auto pr-1">
                  {#each filteredChannelEmojis as emoji (emoji)}
                    <button
                      type="button"
                      class="rounded px-1 py-1 text-lg transition hover:bg-white/10"
                      on:click={() => pickChannelEmoji(emoji)}
                      title={emoji}
                      aria-label={emoji}
                    >
                      {emoji}
                    </button>
                  {/each}
                </div>
                {#if filteredChannelEmojis.length === 0}
                  <p class="mb-2 text-center text-xs text-muted-400">No emoji found.</p>
                {/if}
                <button
                  type="button"
                  class="w-full rounded border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight"
                  on:click={() => {
                    channelEmoji = '';
                    isEmojiPickerOpen = false;
                    emojiSearch = '';
                  }}
                >
                  Clear
                </button>
              </div>
            {/if}
          </div>
        </label>

        <label class="block text-sm text-muted-100">
          Channel type
          <select
            bind:value={channelType}
            class="mt-1 w-full rounded-xl border border-white/15 bg-surface-900 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-accent-400"
          >
            <option value="TEXT">TEXT</option>
            <option value="VOICE">VOICE</option>
          </select>
        </label>

        <label class="block text-sm text-muted-100">
          Topic (optional)
          <input
            bind:value={topic}
            type="text"
            class="mt-1 w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-muted-500 focus:border-accent-400"
            placeholder="Channel description"
          />
        </label>

        <label class="block text-sm text-muted-100">
          Visibility
          <select
            bind:value={isPublic}
            class="mt-1 w-full rounded-xl border border-white/15 bg-surface-900 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-accent-400"
          >
            <option value={true}>Public</option>
            <option value={false}>Private</option>
          </select>
        </label>
      </div>

      <div class="mt-5 flex gap-2">
        <button
          type="submit"
          class="flex-1 rounded-xl bg-accent-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-accent-400 disabled:cursor-not-allowed disabled:bg-surface-800"
          disabled={isSubmitting || !name.trim()}
        >
          {isSubmitting ? 'Creating...' : 'Create'}
        </button>
        <button
          type="button"
          class="rounded-xl border border-white/15 px-4 py-2 text-sm text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
          on:click={requestClose}
          disabled={isSubmitting}
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</div>
