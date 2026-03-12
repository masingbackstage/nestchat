<script lang="ts">
  import { onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { Pencil, Plus, Trash2 } from 'lucide-svelte';
  import type { Message } from '../../types/gateway';

  export let message: Message;
  export let canManage = false;
  export let canReact = true;
  export let isBusy = false;
  export let unicodeEmojis: string[] = [];
  export let customEmojis: Array<{ token: string; label: string; imageUrl: string | null }> = [];

  const dispatch = createEventDispatcher<{
    edit: { messageUuid: string; content: string };
    delete: { messageUuid: string };
    toggleReaction: { messageUuid: string; emoji: string };
  }>();
  let isEditing = false;
  let draft = '';
  let isReactionPickerOpen = false;
  let reactionSearch = '';
  let reactionPickerRoot: HTMLDivElement | null = null;
  $: normalizedReactionSearch = reactionSearch.trim().toLowerCase();
  $: filteredCustomEmojis =
    normalizedReactionSearch.length === 0
      ? customEmojis
      : customEmojis.filter(
          (item) =>
            item.label.toLowerCase().includes(normalizedReactionSearch) ||
            item.token.toLowerCase().includes(normalizedReactionSearch),
        );
  $: filteredUnicodeEmojis =
    normalizedReactionSearch.length === 0
      ? unicodeEmojis
      : unicodeEmojis.filter((emoji) => emoji.includes(normalizedReactionSearch));

  $: formattedTime = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';

  function getInitials(displayName: string): string {
    const parts = displayName.trim().split(/\s+/).filter(Boolean).slice(0, 2);
    if (parts.length === 0) {
      return '?';
    }
    return parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
  }

  function beginEdit(): void {
    if (!canManage || isBusy || message.is_deleted || message.pending) {
      return;
    }
    draft = message.content;
    isEditing = true;
  }

  function cancelEdit(): void {
    isEditing = false;
    draft = '';
  }

  function submitEdit(): void {
    const trimmed = draft.trim();
    if (!trimmed || trimmed === message.content) {
      cancelEdit();
      return;
    }
    dispatch('edit', { messageUuid: message.uuid, content: trimmed });
    isEditing = false;
  }

  function handleEditKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelEdit();
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitEdit();
    }
  }

  function submitDelete(): void {
    if (!canManage || isBusy || message.is_deleted || message.pending) {
      return;
    }
    dispatch('delete', { messageUuid: message.uuid });
  }

  function toggleReaction(emoji: string): void {
    dispatch('toggleReaction', { messageUuid: message.uuid, emoji });
    isReactionPickerOpen = false;
    reactionSearch = '';
  }

  function findCustomEmojiByToken(token: string): { imageUrl: string | null; label: string } | null {
    return customEmojis.find((item) => item.token === token) ?? null;
  }

  function handleDocumentPointerDown(event: PointerEvent): void {
    if (!isReactionPickerOpen || !reactionPickerRoot) {
      return;
    }
    const target = event.target;
    if (!(target instanceof Node)) {
      return;
    }
    if (reactionPickerRoot.contains(target)) {
      return;
    }
    isReactionPickerOpen = false;
  }

  document.addEventListener('pointerdown', handleDocumentPointerDown, true);
  onDestroy(() => {
    document.removeEventListener('pointerdown', handleDocumentPointerDown, true);
  });
</script>

<article
  class={`group rounded-xl px-3 py-2.5 transition-colors hover:bg-white/5 ${message.pending ? 'opacity-55' : ''}`}
>
  <div class="flex items-start gap-3">
    {#if message.avatar_url}
      <img
        src={message.avatar_url}
        alt={message.author}
        class="h-9 w-9 shrink-0 rounded-full object-cover"
      />
    {:else}
      <div
        class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-800 text-[11px] font-semibold text-muted-200"
      >
        {getInitials(message.author)}
      </div>
    {/if}

    <div class="min-w-0 flex-1">
      <header class="relative mb-1 flex min-h-[24px] items-center gap-2 pr-24">
        <span class="text-sm font-semibold text-slate-100">{message.author}</span>
        <time class="text-xs text-muted-400">{formattedTime}</time>
        {#if message.is_edited && !message.is_deleted}
          <span class="text-[10px] uppercase tracking-wide text-muted-500">edited</span>
        {/if}
        {#if message.pending}
          <span class="text-[10px] uppercase tracking-wide text-muted-500">
            {message.failed ? 'failed' : 'sending'}
          </span>
        {/if}
        {#if (canManage || canReact) && !message.pending && !isEditing}
          <div
            bind:this={reactionPickerRoot}
            class={`absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg border border-white/10 bg-surface-900/95 p-0.5 shadow-lg transition-opacity ${
              isReactionPickerOpen
                ? 'pointer-events-auto opacity-100'
                : 'pointer-events-none opacity-0 group-hover:pointer-events-auto group-hover:opacity-100'
            }`}
          >
            {#if !message.is_deleted}
              {#if canReact}
                <button
                  type="button"
                  class="rounded-md p-1 text-muted-300 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-50"
                  on:click={() => {
                    isReactionPickerOpen = !isReactionPickerOpen;
                    if (!isReactionPickerOpen) {
                      reactionSearch = '';
                    }
                  }}
                  disabled={isBusy || message.pending}
                  aria-label="Add reaction"
                  title="Add reaction"
                >
                  <Plus class="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              {/if}
              <button
                type="button"
                class="rounded-md p-1 text-muted-300 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-50"
                on:click={beginEdit}
                disabled={isBusy}
                aria-label="Edit message"
                title="Edit"
              >
                <Pencil class="h-3.5 w-3.5" aria-hidden="true" />
              </button>
              <button
                type="button"
                class="rounded-md p-1 text-red-300 transition hover:bg-red-500/15 hover:text-red-200 disabled:opacity-50"
                on:click={submitDelete}
                disabled={isBusy}
                aria-label="Delete message"
                title="Delete"
              >
                <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            {/if}

            {#if isReactionPickerOpen}
              <div
                class="absolute right-0 top-full z-20 mt-1 w-[280px] rounded-lg border border-white/15 bg-surface-900 p-2 shadow-lg"
              >
                <input
                  type="text"
                  bind:value={reactionSearch}
                  placeholder="Search emoji..."
                  class="mb-2 w-full rounded-md border border-white/15 bg-white/5 px-2 py-1 text-xs text-slate-100 outline-none placeholder:text-muted-500 focus:border-accent-400"
                />

                {#if filteredCustomEmojis.length > 0}
                  <p class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-400">
                    Server emojis
                  </p>
                  <div class="app-scrollbar mb-2 grid max-h-24 grid-cols-8 gap-1 overflow-auto pr-1">
                    {#each filteredCustomEmojis as item (item.token)}
                      <button
                        type="button"
                        class="flex h-8 w-8 items-center justify-center rounded transition hover:bg-white/10"
                        on:click={() => toggleReaction(item.token)}
                        title={`:${item.label}:`}
                        aria-label={`:${item.label}:`}
                        disabled={isBusy || message.pending}
                      >
                        {#if item.imageUrl}
                          <img src={item.imageUrl} alt={item.label} class="h-6 w-6 object-contain" />
                        {:else}
                          <span class="text-xs text-muted-300">:{item.label}:</span>
                        {/if}
                      </button>
                    {/each}
                  </div>
                {/if}

                <p class="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-400">
                  Emoji
                </p>
                <div class="app-scrollbar grid max-h-40 grid-cols-8 gap-1 overflow-auto pr-1">
                  {#each filteredUnicodeEmojis as emoji (emoji)}
                    <button
                      type="button"
                      class="rounded px-1.5 py-1 text-base transition hover:bg-white/10"
                      on:click={() => toggleReaction(emoji)}
                      title={emoji}
                      aria-label={emoji}
                      disabled={isBusy || message.pending}
                    >
                      {emoji}
                    </button>
                  {/each}
                </div>
                {#if filteredCustomEmojis.length === 0 && filteredUnicodeEmojis.length === 0}
                  <p class="mt-2 text-center text-xs text-muted-400">No emoji found.</p>
                {/if}
              </div>
            {/if}
          </div>
        {/if}
      </header>

      {#if message.is_deleted}
        <p class="text-sm italic text-muted-500">Message deleted.</p>
      {:else if isEditing}
        <div class="space-y-2">
      <textarea
        rows="2"
        bind:value={draft}
        on:keydown={handleEditKeydown}
        class="w-full rounded-xl border border-white/15 bg-surface-900/90 px-2.5 py-2 text-sm text-slate-200 outline-none transition focus:border-accent-400"
      ></textarea>
      <div class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-lg border border-white/15 px-2.5 py-1 text-xs text-muted-200 transition hover:border-glass-highlight"
          on:click={cancelEdit}
        >
          Cancel
        </button>
        <button
          type="button"
          class="rounded-lg bg-accent-500 px-2.5 py-1 text-xs text-white transition hover:bg-accent-400"
          on:click={submitEdit}
        >
          Save
        </button>
      </div>
        </div>
      {:else}
        <p class="whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-200">
          {message.content}
        </p>
        <div class="mt-2 flex flex-wrap items-center gap-1.5">
          {#each message.reactions ?? [] as reaction (reaction.emoji)}
            {@const customEmoji = findCustomEmojiByToken(reaction.emoji)}
            <button
              type="button"
              class={`rounded-full border px-2 py-0.5 text-xs transition ${
                reaction.reacted_by_me
                  ? 'border-accent-500/45 bg-accent-500/25 text-accent-300'
                  : 'border-white/15 bg-white/5 text-muted-200 hover:border-glass-highlight'
              }`}
              on:click={() => toggleReaction(reaction.emoji)}
              title={`Reaction ${reaction.emoji}`}
              disabled={isBusy || message.pending}
            >
              {#if customEmoji?.imageUrl}
                <img
                  src={customEmoji.imageUrl}
                  alt={customEmoji.label}
                  class="inline-block h-4 w-4 object-contain align-[-0.125rem]"
                />
              {:else}
                <span>{reaction.emoji}</span>
              {/if}
              <span class="ml-1">{reaction.count}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</article>
