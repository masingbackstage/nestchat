<script lang="ts">
  import { tick } from 'svelte';
  import { fade, scale } from 'svelte/transition';
  import { Bell, Hash, HelpCircle, Pin, Search, Users } from 'lucide-svelte';
  import { getCurrentUserUuid } from '../../lib/auth';
  import { sendDeleteMessage, sendEditMessage, sendToggleReaction } from '../../lib/socket';
  import { pushToast } from '../../lib/stores/toast';
  import { activeChannel, activeServer } from '../../lib/stores/ui';
  import {
    channelQueryStateById,
    lastReadMessageUuidByChannel,
    loadNewerMessages,
    loadOlderMessages,
    messagesByChannel,
    unreadCountByChannel,
  } from './messages.store';
  import MessageItem from './MessageItem.svelte';
  import MessageInput from './MessageInput.svelte';

  let messagesContainer: HTMLDivElement | null = null;
  let loadingOlderFromScroll = false;
  let loadingNewerFromScroll = false;
  let lastAutoScrolledChannelUuid: string | null = null;
  let previousChannelUuid: string | null = null;
  let previousMessageCount = 0;
  let isViewportNearBottom = true;
  let busyMessageActions = new Set<string>();
  let currentUserUuid: string | null = null;
  let pendingDeleteMessageUuid: string | null = null;
  let isDeleteConfirmSubmitting = false;

  $: currentMessages = $activeChannel ? ($messagesByChannel[$activeChannel.uuid] ?? []) : [];
  $: currentChannelQuery = $activeChannel ? $channelQueryStateById[$activeChannel.uuid] : null;
  $: currentUnreadCount = $activeChannel ? ($unreadCountByChannel[$activeChannel.uuid] ?? 0) : 0;
  $: currentLastReadMessageUuid = $activeChannel
    ? ($lastReadMessageUuidByChannel[$activeChannel.uuid] ?? null)
    : null;
  $: firstNewMessageIndex = getFirstNewMessageIndex(
    currentMessages,
    currentUnreadCount,
    currentLastReadMessageUuid,
  );
  $: isInitialLoading = Boolean(
    $activeChannel && currentMessages.length === 0 && currentChannelQuery?.isLoadingInitial,
  );
  $: if (
    $activeChannel?.uuid &&
    messagesContainer &&
    currentMessages.length > 0 &&
    !isInitialLoading &&
    lastAutoScrolledChannelUuid !== $activeChannel.uuid
  ) {
    void scrollToBottomForChannel($activeChannel.uuid);
  }
  $: if ($activeChannel?.uuid && messagesContainer) {
    const channelChanged = previousChannelUuid !== $activeChannel.uuid;
    const hadMoreMessages = currentMessages.length > previousMessageCount;

    if (!channelChanged && hadMoreMessages && isNearBottom(messagesContainer)) {
      void scrollToBottomForChannel($activeChannel.uuid);
    }

    previousChannelUuid = $activeChannel.uuid;
    previousMessageCount = currentMessages.length;
    isViewportNearBottom = isNearBottom(messagesContainer);
  } else if (!$activeChannel?.uuid) {
    previousChannelUuid = null;
    previousMessageCount = 0;
    isViewportNearBottom = true;
  }
  $: currentUserUuid = getCurrentUserUuid();

  async function scrollToBottomForChannel(channelUuid: string): Promise<void> {
    await tick();
    if (!messagesContainer || $activeChannel?.uuid !== channelUuid) {
      return;
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    lastAutoScrolledChannelUuid = channelUuid;
    isViewportNearBottom = true;
  }

  async function maybeLoadOlderMessages(): Promise<void> {
    if (
      !$activeChannel ||
      !messagesContainer ||
      loadingOlderFromScroll ||
      !currentChannelQuery?.hasMoreOlder ||
      !currentChannelQuery?.nextBefore ||
      currentChannelQuery.isLoadingOlder
    ) {
      return;
    }

    if (messagesContainer.scrollTop > 40) {
      return;
    }

    loadingOlderFromScroll = true;
    const previousScrollHeight = messagesContainer.scrollHeight;

    await loadOlderMessages($activeChannel.uuid);
    await tick();

    if (messagesContainer) {
      const delta = messagesContainer.scrollHeight - previousScrollHeight;
      messagesContainer.scrollTop += Math.max(0, delta);
      isViewportNearBottom = isNearBottom(messagesContainer);
    }

    loadingOlderFromScroll = false;
  }

  function isNearBottom(container: HTMLDivElement): boolean {
    const distanceFromBottom = container.scrollHeight - (container.scrollTop + container.clientHeight);
    return distanceFromBottom <= 80;
  }

  async function maybeLoadNewerMessages(): Promise<void> {
    if (
      !$activeChannel ||
      !messagesContainer ||
      loadingNewerFromScroll ||
      !currentChannelQuery?.hasMoreNewer ||
      !currentChannelQuery?.nextAfter ||
      currentChannelQuery.isLoadingNewer
    ) {
      return;
    }

    if (!isNearBottom(messagesContainer)) {
      return;
    }

    loadingNewerFromScroll = true;
    const previousFromBottom =
      messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;

    await loadNewerMessages($activeChannel.uuid);
    await tick();

    if (messagesContainer) {
      messagesContainer.scrollTop = Math.max(
        0,
        messagesContainer.scrollHeight - messagesContainer.clientHeight - previousFromBottom,
      );
      isViewportNearBottom = isNearBottom(messagesContainer);
    }

    loadingNewerFromScroll = false;
  }

  function handleScroll(): void {
    if (messagesContainer) {
      isViewportNearBottom = isNearBottom(messagesContainer);
    }
    void maybeLoadOlderMessages();
    void maybeLoadNewerMessages();
  }

  async function jumpToLatest(): Promise<void> {
    if (!$activeChannel || !messagesContainer) {
      return;
    }

    if (currentChannelQuery?.hasMoreNewer && !currentChannelQuery.isLoadingNewer) {
      await loadNewerMessages($activeChannel.uuid);
      await tick();
    }

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    isViewportNearBottom = true;
  }

  function getFirstNewMessageIndex(
    messages: { uuid: string }[],
    unreadCount: number,
    lastReadMessageUuid: string | null,
  ): number {
    if (messages.length === 0 || unreadCount <= 0) {
      return -1;
    }

    if (lastReadMessageUuid) {
      const idx = messages.findIndex((message) => message.uuid === lastReadMessageUuid);
      if (idx >= 0) {
        return Math.min(messages.length, idx + 1);
      }
    }

    return Math.max(0, messages.length - unreadCount);
  }

  function canManageMessage(message: { author_uuid?: string; pending?: boolean; is_deleted?: boolean }): boolean {
    if (message.pending) {
      return false;
    }
    const isOwner = Boolean($activeServer?.isOwner ?? $activeServer?.is_owner ?? false);
    const isAuthor = Boolean(currentUserUuid && message.author_uuid === currentUserUuid);
    return isOwner || isAuthor;
  }

  function isMessageBusy(messageUuid: string): boolean {
    return busyMessageActions.has(messageUuid);
  }

  function markBusy(messageUuid: string, busy: boolean): void {
    const next = new Set(busyMessageActions);
    if (busy) {
      next.add(messageUuid);
    } else {
      next.delete(messageUuid);
    }
    busyMessageActions = next;
  }

  async function handleEditMessage(
    event: CustomEvent<{ messageUuid: string; content: string }>,
  ): Promise<void> {
    const { messageUuid, content } = event.detail;
    markBusy(messageUuid, true);
    const sent = sendEditMessage(messageUuid, content);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    }
    await tick();
    markBusy(messageUuid, false);
  }

  function handleToggleReaction(
    event: CustomEvent<{ messageUuid: string; emoji: string }>,
  ): void {
    const { messageUuid, emoji } = event.detail;
    const sent = sendToggleReaction(messageUuid, emoji);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    }
  }

  function handleDeleteMessage(event: CustomEvent<{ messageUuid: string }>): void {
    pendingDeleteMessageUuid = event.detail.messageUuid;
  }

  function cancelDeleteConfirmation(): void {
    if (isDeleteConfirmSubmitting) {
      return;
    }
    pendingDeleteMessageUuid = null;
  }

  function handleDeleteOverlayClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      cancelDeleteConfirmation();
    }
  }

  async function confirmDeleteMessage(): Promise<void> {
    if (!pendingDeleteMessageUuid) {
      return;
    }

    const messageUuid = pendingDeleteMessageUuid;
    isDeleteConfirmSubmitting = true;
    markBusy(messageUuid, true);
    const sent = sendDeleteMessage(messageUuid);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
      isDeleteConfirmSubmitting = false;
      markBusy(messageUuid, false);
      return;
    }
    await tick();
    pendingDeleteMessageUuid = null;
    isDeleteConfirmSubmitting = false;
    markBusy(messageUuid, false);
  }
</script>

<section class="glass-panel flex min-w-0 flex-1 flex-col rounded-panel" aria-label="Chat">
  <header class="flex h-16 items-center border-b border-white/10 px-5">
    {#if $activeChannel}
      <Hash class="h-5 w-5 text-muted-400" aria-hidden="true" />
      <h2 class="truncate text-lg font-semibold text-slate-100">{$activeChannel.name}</h2>
      <span class="mx-3 h-4 w-px bg-white/15"></span>
    {:else}
      <h2 class="text-lg font-semibold text-slate-100">Select a channel</h2>
    {/if}

    <div class="ml-auto hidden items-center gap-4 text-muted-300 md:flex">
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Powiadomienia">
        <Bell class="h-4 w-4" />
      </button>
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Pinned">
        <Pin class="h-4 w-4" />
      </button>
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Members">
        <Users class="h-4 w-4" />
      </button>
      <div class="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5">
        <input
          type="text"
          readonly
          value=""
          placeholder="Search"
          class="w-24 bg-transparent text-xs text-muted-200 outline-none placeholder:text-muted-500"
        />
        <Search class="h-3.5 w-3.5 text-muted-400" />
      </div>
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Help">
        <HelpCircle class="h-4 w-4" />
      </button>
    </div>

  </header>

  <div class="flex min-h-0 flex-1 flex-col">
    <div class="app-scrollbar flex-1 space-y-1 overflow-auto px-4 py-4" bind:this={messagesContainer} on:scroll={handleScroll}>
      {#if $activeChannel && (currentChannelQuery?.isLoadingOlder || currentChannelQuery?.hasMoreOlder)}
        <p class="mb-2 text-xs text-muted-300">
          {#if currentChannelQuery?.isLoadingOlder}
            Loading older messages...
          {:else}
            Older messages available.
          {/if}
        </p>
      {/if}

      {#if !$activeChannel}
        <p class="text-sm text-muted-300">Select a server and channel to start chatting.</p>
      {:else if isInitialLoading}
        <p class="text-sm text-muted-300">Loading messages...</p>
      {:else if currentMessages.length === 0}
        <div class="rounded-2xl border border-white/10 bg-white/5 p-5">
          <div class="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-500/20 text-accent-300">
            <Hash class="h-6 w-6" />
          </div>
          <p class="text-2xl font-semibold text-slate-100">Welcome to #{$activeChannel.name}!</p>
          <p class="mt-2 text-sm text-muted-200">This is the start of this channel. Send the first message.</p>
        </div>
      {:else}
        {#each currentMessages as message, index (message.uuid)}
          {#if firstNewMessageIndex === index}
            <div class="my-2 flex items-center gap-2">
              <div class="h-px flex-1 bg-accent-500/50"></div>
              <p class="text-[11px] font-semibold uppercase tracking-wide text-accent-300">
                New messages
              </p>
              <div class="h-px flex-1 bg-accent-500/50"></div>
            </div>
          {/if}
          <MessageItem
            {message}
            canManage={canManageMessage(message)}
            isBusy={isMessageBusy(message.uuid)}
            on:edit={handleEditMessage}
            on:delete={handleDeleteMessage}
            on:toggleReaction={handleToggleReaction}
          />
        {/each}
      {/if}

      {#if $activeChannel && currentChannelQuery?.error}
        <p class="mt-2 text-xs text-amber-200">
          Failed to refresh messages. Showing the latest cached version.
        </p>
      {/if}

      {#if $activeChannel && currentChannelQuery?.isLoadingNewer}
        <p class="mt-2 text-xs text-muted-300">
          Loading newer messages...
        </p>
      {/if}
    </div>

    {#if $activeChannel && currentChannelQuery?.hasMoreNewer && !isViewportNearBottom}
      <div class="px-4 pb-2">
        <button
          type="button"
          class="rounded-pill border border-accent-500/35 bg-accent-500/15 px-3 py-1 text-xs text-accent-300 transition hover:bg-accent-500/25"
          on:click={jumpToLatest}
        >
          Newer messages available
        </button>
      </div>
    {/if}

    <MessageInput />
  </div>
</section>

{#if pendingDeleteMessageUuid}
  <div
    class="fixed inset-0 z-[70] flex items-center justify-center bg-surface-950/75 p-4 backdrop-blur-sm"
    role="presentation"
    on:click={handleDeleteOverlayClick}
    in:fade={{ duration: 130 }}
    out:fade={{ duration: 120 }}
  >
    <div
      class="glass-panel-strong w-full max-w-sm rounded-2xl p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-message-title"
      tabindex="-1"
      in:scale={{ duration: 170, start: 0.96 }}
      out:scale={{ duration: 120, start: 1 }}
    >
      <h3 id="delete-message-title" class="text-base font-semibold text-slate-100">
        Delete this message?
      </h3>
      <p class="mt-2 text-sm text-muted-200">
        This action cannot be undone.
      </p>
      <div class="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-xl border border-white/15 px-3 py-1.5 text-sm text-muted-200 transition hover:border-glass-highlight disabled:opacity-60"
          on:click={cancelDeleteConfirmation}
          disabled={isDeleteConfirmSubmitting}
        >
          Cancel
        </button>
        <button
          type="button"
          class="rounded-xl bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-60"
          on:click={confirmDeleteMessage}
          disabled={isDeleteConfirmSubmitting}
        >
          {isDeleteConfirmSubmitting ? 'Deleting...' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{/if}
