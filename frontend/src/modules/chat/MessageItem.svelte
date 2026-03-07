<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Pencil, Plus, Trash2 } from 'lucide-svelte';
  import type { Message } from '../../types/gateway';

  export let message: Message;
  export let canManage = false;
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

<article class={`group rounded-md px-3 py-2 hover:bg-slate-800/50 ${message.pending ? 'opacity-55' : ''}`}>
  <header class="relative mb-1 flex items-center gap-2 pr-14">
    <span class="text-sm font-semibold text-slate-100">{message.author}</span>
    <time class="text-xs text-slate-500">{formattedTime}</time>
    {#if message.is_edited && !message.is_deleted}
      <span class="text-[10px] uppercase tracking-wide text-slate-500">edytowano</span>
    {/if}
    {#if message.pending}
      <span class="text-[10px] uppercase tracking-wide text-slate-500">
        {message.failed ? 'failed' : 'sending'}
      </span>
    {/if}
    {#if canManage && !message.pending && !isEditing}
      <div
        class="pointer-events-none absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100"
      >
        {#if !message.is_deleted}
          <button
            type="button"
            class="rounded p-1 text-slate-400 transition hover:bg-slate-700/70 hover:text-slate-200 disabled:opacity-50"
            on:click={beginEdit}
            disabled={isBusy}
            aria-label="Edytuj wiadomość"
            title="Edytuj"
          >
            <Pencil class="h-3.5 w-3.5" aria-hidden="true" />
          </button>
          <button
            type="button"
            class="rounded p-1 text-red-300 transition hover:bg-red-500/10 hover:text-red-200 disabled:opacity-50"
            on:click={submitDelete}
            disabled={isBusy}
            aria-label="Usuń wiadomość"
            title="Usuń"
          >
            <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        {/if}
      </div>
    {/if}
  </header>

  {#if message.is_deleted}
    <p class="text-sm italic text-slate-500">Wiadomość usunięta.</p>
  {:else if isEditing}
    <div class="space-y-2">
      <textarea
        rows="2"
        bind:value={draft}
        on:keydown={handleEditKeydown}
        class="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200 outline-none transition focus:border-indigo-500"
      ></textarea>
      <div class="flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-slate-500"
          on:click={cancelEdit}
        >
          Anuluj
        </button>
        <button
          type="button"
          class="rounded bg-indigo-600 px-2 py-1 text-xs text-white transition hover:bg-indigo-500"
          on:click={submitEdit}
        >
          Zapisz
        </button>
      </div>
    </div>
  {:else}
    <p class="whitespace-pre-wrap break-words text-sm text-slate-300">{message.content}</p>
    <div class="relative mt-2 flex flex-wrap items-center gap-1.5">
      {#each message.reactions ?? [] as reaction (reaction.emoji)}
        <button
          type="button"
          class={`rounded-full border px-2 py-0.5 text-xs transition ${
            reaction.reacted_by_me
              ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-100'
              : 'border-slate-700 bg-slate-800 text-slate-300 hover:border-slate-500'
          }`}
          on:click={() => toggleReaction(reaction.emoji)}
          title={`Reakcja ${reaction.emoji}`}
          disabled={isBusy || message.pending}
        >
          <span>{reaction.emoji}</span>
          <span class="ml-1">{reaction.count}</span>
        </button>
      {/each}
      <button
        type="button"
        class={`rounded-full border border-slate-700 bg-slate-800 p-1 text-slate-400 transition hover:border-slate-500 hover:text-slate-200 ${
          isReactionPickerOpen
            ? 'opacity-100'
            : 'pointer-events-none opacity-0 group-hover:pointer-events-auto group-hover:opacity-100'
        }`}
        on:click={() => (isReactionPickerOpen = !isReactionPickerOpen)}
        disabled={isBusy || message.pending}
        aria-label="Dodaj reakcję"
        title="Dodaj reakcję"
      >
        <Plus class="h-3.5 w-3.5" aria-hidden="true" />
      </button>

      {#if isReactionPickerOpen}
        <div class="absolute left-0 top-full z-20 mt-1 flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-lg">
          {#each REACTION_EMOJIS as emoji (emoji)}
            <button
              type="button"
              class="rounded px-1.5 py-1 text-base transition hover:bg-slate-700"
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
</article>
