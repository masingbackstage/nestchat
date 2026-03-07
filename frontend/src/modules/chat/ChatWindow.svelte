<script lang="ts">
  import { tick } from 'svelte';
  import { activeChannel } from '../../lib/stores/ui';
  import {
    MAX_MESSAGES_PER_CHANNEL,
    channelQueryStateById,
    chatConnectionStatus,
    loadNewerMessages,
    loadOlderMessages,
    messagesByChannel,
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

  $: currentMessages = $activeChannel ? ($messagesByChannel[$activeChannel.uuid] ?? []) : [];
  $: currentChannelQuery = $activeChannel ? $channelQueryStateById[$activeChannel.uuid] : null;
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
        {#each currentMessages as message (message.uuid)}
          <MessageItem {message} />
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
