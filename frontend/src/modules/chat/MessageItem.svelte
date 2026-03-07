<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Pencil, Plus, Trash2 } from 'lucide-svelte';
  import type { Message } from '../../types/gateway';

  export let message: Message;
  export let canManage = false;
  export let canReact = true;
  export let isBusy = false;

  const dispatch = createEventDispatcher<{
    edit: { messageUuid: string; content: string };
    delete: { messageUuid: string };
    toggleReaction: { messageUuid: string; emoji: string };
  }>();
  const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '😡', '🎉', '👀'];

  let isEditing = false;
  let draft = '';
  let isReactionPickerOpen = false;

  $: formattedTime = message.created_at
    ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';

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
  }
</script>

<article
  class={`group rounded-xl px-3 py-2.5 transition-colors hover:bg-white/5 ${message.pending ? 'opacity-55' : ''}`}
>
  <header class="relative mb-1 flex min-h-[24px] items-center gap-2 pr-24">
    <span class="text-sm font-semibold text-slate-100">{message.author}</span>
    <time class="text-xs text-muted-400">{formattedTime}</time>
    {#if message.is_edited && !message.is_deleted}
      <span class="text-[10px] uppercase tracking-wide text-muted-500">edytowano</span>
    {/if}
    {#if message.pending}
      <span class="text-[10px] uppercase tracking-wide text-muted-500">
        {message.failed ? 'failed' : 'sending'}
      </span>
    {/if}
    {#if (canManage || canReact) && !message.pending && !isEditing}
      <div
        class="pointer-events-none absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg border border-white/10 bg-surface-900/95 p-0.5 opacity-0 shadow-lg transition-opacity group-hover:pointer-events-auto group-hover:opacity-100"
      >
        {#if !message.is_deleted}
          {#if canReact}
            <button
              type="button"
              class="rounded-md p-1 text-muted-300 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-50"
              on:click={() => (isReactionPickerOpen = !isReactionPickerOpen)}
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
            class="absolute right-0 top-full z-20 mt-1 flex items-center gap-1 rounded-lg border border-white/15 bg-surface-900 p-1 shadow-lg"
          >
            {#each REACTION_EMOJIS as emoji (emoji)}
              <button
                type="button"
                class="rounded px-1.5 py-1 text-base transition hover:bg-white/10"
                on:click={() => toggleReaction(emoji)}
                title={emoji}
                aria-label={`Reakcja ${emoji}`}
                disabled={isBusy || message.pending}
              >
                {emoji}
              </button>
            {/each}
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
        <button
          type="button"
          class={`rounded-full border px-2 py-0.5 text-xs transition ${
            reaction.reacted_by_me
              ? 'border-accent-500/45 bg-accent-500/25 text-accent-300'
              : 'border-white/15 bg-white/5 text-muted-200 hover:border-glass-highlight'
          }`}
          on:click={() => toggleReaction(reaction.emoji)}
          title={`Reakcja ${reaction.emoji}`}
          disabled={isBusy || message.pending}
        >
          <span>{reaction.emoji}</span>
          <span class="ml-1">{reaction.count}</span>
        </button>
      {/each}
    </div>
  {/if}
</article>
