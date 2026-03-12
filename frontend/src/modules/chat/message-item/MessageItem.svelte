<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Message } from '../../../types/gateway';
  import { findCustomEmojiByToken, formatMessageTime, getInitials } from './utils';
  import ReactionPicker from './ReactionPicker.svelte';

  export let message: Message;
  export let canManage = false;
  export let canReact = true;
  export let isBusy = false;
  export let unicodeEmojis: string[] = [];
  export let customEmojis: { token: string; label: string; imageUrl: string | null }[] = [];

  const dispatch = createEventDispatcher<{
    edit: { messageUuid: string; content: string };
    delete: { messageUuid: string };
    toggleReaction: { messageUuid: string; emoji: string };
  }>();
  let isEditing = false;
  let draft = '';
  let isHovered = false;
  $: formattedTime = formatMessageTime(message.created_at);

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
  }
</script>

<article
  class:message-item-pending={message.pending}
  class="message-item"
  on:mouseenter={() => {
    isHovered = true;
  }}
  on:mouseleave={() => {
    isHovered = false;
  }}
>
  <div class="message-item-row">
    {#if message.avatar_url}
      <img src={message.avatar_url} alt={message.author} class="message-item-avatar" />
    {:else}
      <div class="message-item-avatar message-item-avatar-fallback">
        {getInitials(message.author)}
      </div>
    {/if}

    <div class="message-item-content">
      <header class="message-item-header">
        <span class="message-item-author">{message.author}</span>
        <time class="message-item-time">{formattedTime}</time>
        {#if message.is_edited && !message.is_deleted}
          <span class="message-item-status-flag">edited</span>
        {/if}
        {#if message.pending}
          <span class="message-item-status-flag">
            {message.failed ? 'failed' : 'sending'}
          </span>
        {/if}
        <ReactionPicker
          {canManage}
          {canReact}
          {isBusy}
          isDeleted={Boolean(message.is_deleted)}
          isPending={Boolean(message.pending)}
          {isEditing}
          isVisible={isHovered}
          {customEmojis}
          {unicodeEmojis}
          onEdit={beginEdit}
          onDelete={submitDelete}
          onToggleReaction={toggleReaction}
        />
      </header>

      {#if message.is_deleted}
        <p class="message-item-deleted-copy">Message deleted.</p>
      {:else if isEditing}
        <div class="message-item-editing">
          <textarea
            rows="2"
            bind:value={draft}
            on:keydown={handleEditKeydown}
            class="message-item-edit-textarea"
          ></textarea>
          <div class="message-item-edit-actions">
            <button
              type="button"
              class="message-item-edit-button message-item-edit-button-secondary"
              on:click={cancelEdit}
            >
              Cancel
            </button>
            <button
              type="button"
              class="message-item-edit-button message-item-edit-button-primary"
              on:click={submitEdit}
            >
              Save
            </button>
          </div>
        </div>
      {:else}
        <p class="message-item-body">
          {message.content}
        </p>
        <div class="message-item-reactions">
          {#each message.reactions ?? [] as reaction (reaction.emoji)}
            {@const customEmoji = findCustomEmojiByToken(customEmojis, reaction.emoji)}
            <button
              type="button"
              class:message-item-reaction-active={reaction.reacted_by_me}
              class:message-item-reaction-inactive={!reaction.reacted_by_me}
              class="message-item-reaction-pill"
              on:click={() => toggleReaction(reaction.emoji)}
              title={`Reaction ${reaction.emoji}`}
              disabled={isBusy || message.pending}
            >
              {#if customEmoji?.imageUrl}
                <img
                  src={customEmoji.imageUrl}
                  alt={customEmoji.label}
                  class="message-item-reaction-image"
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

<style>
  .message-item {
    @apply rounded-xl px-3 py-2.5 transition-colors hover:bg-white/5;
  }

  .message-item-pending {
    @apply opacity-55;
  }

  .message-item-row {
    @apply flex items-start gap-3;
  }

  .message-item-avatar {
    @apply h-9 w-9 shrink-0 rounded-full object-cover;
  }

  .message-item-avatar-fallback {
    @apply flex items-center justify-center bg-surface-800 text-[11px] font-semibold text-muted-200;
  }

  .message-item-content {
    @apply min-w-0 flex-1;
  }

  .message-item-header {
    @apply relative mb-1 flex min-h-[24px] items-center gap-2 pr-24;
  }

  .message-item-author {
    @apply text-sm font-semibold text-slate-100;
  }

  .message-item-time {
    @apply text-xs text-muted-400;
  }

  .message-item-status-flag {
    @apply text-[10px] uppercase tracking-wide text-muted-500;
  }

  .message-item-deleted-copy {
    @apply text-sm italic text-muted-500;
  }

  .message-item-editing {
    @apply space-y-2;
  }

  .message-item-edit-textarea {
    @apply w-full rounded-xl border border-white/15 bg-surface-900/90 px-2.5 py-2 text-sm text-slate-200 outline-none transition focus:border-accent-400;
  }

  .message-item-edit-actions {
    @apply flex items-center justify-end gap-2;
  }

  .message-item-edit-button {
    @apply rounded-lg px-2.5 py-1 text-xs transition;
  }

  .message-item-edit-button-secondary {
    @apply border border-white/15 text-muted-200 hover:border-glass-highlight;
  }

  .message-item-edit-button-primary {
    @apply bg-accent-500 text-white hover:bg-accent-400;
  }

  .message-item-body {
    @apply whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-200;
  }

  .message-item-reactions {
    @apply mt-2 flex flex-wrap items-center gap-1.5;
  }

  .message-item-reaction-pill {
    @apply rounded-full border px-2 py-0.5 text-xs transition;
  }

  .message-item-reaction-active {
    @apply border-accent-500/45 bg-accent-500/25 text-accent-300;
  }

  .message-item-reaction-inactive {
    @apply border-white/15 bg-white/5 text-muted-200 hover:border-glass-highlight;
  }

  .message-item-reaction-image {
    @apply inline-block h-4 w-4 object-contain align-[-0.125rem];
  }
</style>
