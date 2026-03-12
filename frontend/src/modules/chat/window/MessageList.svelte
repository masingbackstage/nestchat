<script lang="ts">
  import { Hash } from 'lucide-svelte';
  import MessageItem from '../message-item';
  import type { Message } from '../../../types/gateway';
  import type { WindowChannelQueryState, WindowReactionEmoji } from './types';

  export let activeChannelName: string | null = null;
  export let hasActiveChannel = false;
  export let isInitialLoading = false;
  export let currentMessages: Message[] = [];
  export let currentChannelQuery: WindowChannelQueryState | null = null;
  export let firstNewMessageIndex = -1;
  export let canManageMessage: (message: Message) => boolean;
  export let isMessageBusy: (messageUuid: string) => boolean;
  export let unicodeEmojis: string[] = [];
  export let customReactionEmojis: WindowReactionEmoji[] = [];
</script>

{#if hasActiveChannel && (currentChannelQuery?.isLoadingOlder || currentChannelQuery?.hasMoreOlder)}
  <p class="message-list-meta">
    {#if currentChannelQuery?.isLoadingOlder}
      Loading older messages...
    {:else}
      Older messages available.
    {/if}
  </p>
{/if}

{#if !hasActiveChannel}
  <p class="message-list-state-copy">Select a server and channel to start chatting.</p>
{:else if isInitialLoading}
  <p class="message-list-state-copy">Loading messages...</p>
{:else if currentMessages.length === 0}
  <div class="message-list-empty-state">
    <div class="message-list-empty-icon">
      <Hash class="h-6 w-6" />
    </div>
    <p class="message-list-empty-title">Welcome to #{activeChannelName}!</p>
    <p class="message-list-empty-copy">
      This is the start of this channel. Send the first message.
    </p>
  </div>
{:else}
  {#each currentMessages as message, index (message.uuid)}
    {#if firstNewMessageIndex === index}
      <div class="message-list-divider">
        <div class="message-list-divider-line"></div>
        <p class="message-list-divider-label">
          New messages
        </p>
        <div class="message-list-divider-line"></div>
      </div>
    {/if}
    <MessageItem
      {message}
      canManage={canManageMessage(message)}
      isBusy={isMessageBusy(message.uuid)}
      unicodeEmojis={unicodeEmojis}
      customEmojis={customReactionEmojis}
      on:edit
      on:delete
      on:toggleReaction
    />
  {/each}
{/if}

{#if hasActiveChannel && currentChannelQuery?.error}
  <p class="message-list-error">
    Failed to refresh messages. Showing the latest cached version.
  </p>
{/if}

{#if hasActiveChannel && currentChannelQuery?.isLoadingNewer}
  <p class="message-list-meta message-list-meta-spaced">Loading newer messages...</p>
{/if}

<style>
  .message-list-meta {
    @apply mb-2 text-xs text-muted-300;
  }

  .message-list-meta-spaced {
    @apply mt-2 mb-0;
  }

  .message-list-state-copy {
    @apply text-sm text-muted-300;
  }

  .message-list-empty-state {
    @apply rounded-2xl border border-white/10 bg-white/5 p-5;
  }

  .message-list-empty-icon {
    @apply mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-500/20 text-accent-300;
  }

  .message-list-empty-title {
    @apply text-2xl font-semibold text-slate-100;
  }

  .message-list-empty-copy {
    @apply mt-2 text-sm text-muted-200;
  }

  .message-list-divider {
    @apply my-2 flex items-center gap-2;
  }

  .message-list-divider-line {
    @apply h-px flex-1 bg-accent-500/50;
  }

  .message-list-divider-label {
    @apply text-[11px] font-semibold uppercase tracking-wide text-accent-300;
  }

  .message-list-error {
    @apply mt-2 text-xs text-amber-200;
  }
</style>
