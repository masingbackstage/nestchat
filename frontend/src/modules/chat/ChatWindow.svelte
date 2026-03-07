<script lang="ts">
  import { tick } from 'svelte';
  import { getCurrentUserUuid } from '../../lib/auth';
  import { sendDeleteMessage, sendEditMessage } from '../../lib/socket';
  import { pushToast } from '../../lib/stores/toast';
  import { activeChannel, activeServer } from '../../lib/stores/ui';
  import {
    MAX_MESSAGES_PER_CHANNEL,
    channelQueryStateById,
    chatConnectionStatus,
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
      pushToast({ type: 'error', message: 'Brak połączenia z gateway.' });
    }
    await tick();
    markBusy(messageUuid, false);
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
      pushToast({ type: 'error', message: 'Brak połączenia z gateway.' });
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

<section class="flex min-w-0 flex-1 flex-col bg-app-850" aria-label="Chat">
  <header
    class="flex h-12 items-center gap-2 border-b border-slate-700 px-4 text-sm font-bold text-slate-100"
  >
    {#if $activeChannel}
      <span aria-hidden="true" class="text-slate-500">#</span>
      <h2 class="truncate">{$activeChannel.name}</h2>
      <span class="rounded bg-slate-800 px-2 py-0.5 text-xs font-normal text-slate-400">
        {currentMessages.length}/{MAX_MESSAGES_PER_CHANNEL}
      </span>
    {:else}
      <h2>Wybierz kanał</h2>
    {/if}

    <span class="ml-auto rounded bg-slate-800 px-2 py-0.5 text-xs font-normal text-slate-400">
      WS: {$chatConnectionStatus}
    </span>
  </header>

  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex-1 space-y-1 overflow-auto p-3" bind:this={messagesContainer} on:scroll={handleScroll}>
      {#if $activeChannel && (currentChannelQuery?.isLoadingOlder || currentChannelQuery?.hasMoreOlder)}
        <p class="mb-2 text-xs text-slate-400">
          {#if currentChannelQuery?.isLoadingOlder}
            Ładowanie starszych wiadomości...
          {:else}
            Dostępne starsze wiadomości.
          {/if}
        </p>
      {/if}

      {#if !$activeChannel}
        <p class="text-sm text-slate-400">Wybierz serwer i kanał, aby rozpocząć rozmowę.</p>
      {:else if isInitialLoading}
        <p class="text-sm text-slate-400">Ładowanie wiadomości...</p>
      {:else if currentMessages.length === 0}
        <p class="text-sm text-slate-400">Brak wiadomości na tym kanale.</p>
      {:else}
        {#each currentMessages as message, index (message.uuid)}
          {#if firstNewMessageIndex === index}
            <div class="my-2 flex items-center gap-2">
              <div class="h-px flex-1 bg-emerald-500/40"></div>
              <p class="text-[11px] font-semibold uppercase tracking-wide text-emerald-300">
                Nowe wiadomości
              </p>
              <div class="h-px flex-1 bg-emerald-500/40"></div>
            </div>
          {/if}
          <MessageItem
            {message}
            canManage={canManageMessage(message)}
            isBusy={isMessageBusy(message.uuid)}
            on:edit={handleEditMessage}
            on:delete={handleDeleteMessage}
          />
        {/each}
      {/if}

      {#if $activeChannel && currentChannelQuery?.error}
        <p class="mt-2 text-xs text-amber-300">
          Nie udało się odświeżyć wiadomości. Pokazuję ostatnią dostępną wersję.
        </p>
      {/if}

      {#if $activeChannel && currentChannelQuery?.isLoadingNewer}
        <p class="mt-2 text-xs text-slate-400">
          Ładowanie nowszych wiadomości...
        </p>
      {/if}
    </div>

    {#if $activeChannel && currentChannelQuery?.hasMoreNewer && !isViewportNearBottom}
      <div class="px-3 pb-2">
        <button
          type="button"
          class="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200 transition hover:bg-emerald-500/20"
          on:click={jumpToLatest}
        >
          Dostępne nowsze wiadomości
        </button>
      </div>
    {/if}

    <MessageInput />
  </div>
</section>

{#if pendingDeleteMessageUuid}
  <div
    class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 p-4"
    role="presentation"
    on:click={handleDeleteOverlayClick}
  >
    <div
      class="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-message-title"
      tabindex="-1"
    >
      <h3 id="delete-message-title" class="text-base font-semibold text-slate-100">
        Usunąć wiadomość?
      </h3>
      <p class="mt-2 text-sm text-slate-400">
        Tej operacji nie da się cofnąć.
      </p>
      <div class="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:border-slate-500 disabled:opacity-60"
          on:click={cancelDeleteConfirmation}
          disabled={isDeleteConfirmSubmitting}
        >
          Anuluj
        </button>
        <button
          type="button"
          class="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-red-500 disabled:opacity-60"
          on:click={confirmDeleteMessage}
          disabled={isDeleteConfirmSubmitting}
        >
          {isDeleteConfirmSubmitting ? 'Usuwanie...' : 'Usuń'}
        </button>
      </div>
    </div>
  </div>
{/if}
