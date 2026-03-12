<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { getCurrentUserUuid } from '../../../lib/auth';
  import { UNICODE_EMOJI_PICKER } from '../../../lib/emoji';
  import { activeChannel, activeServer } from '../../../lib/stores/ui';
  import type { WindowViewModel } from './types';
  import { ensureServerEmojis, serverEmojisByServer } from '../../servers/emojis/store';
  import MessageInput from '../message-input';
  import {
    channelQueryStateById,
    lastReadMessageUuidByChannel,
    messagesByChannel,
    unreadCountByChannel,
  } from '../messages';
  import ChatHeader from './ChatHeader.svelte';
  import DeleteMessageModal from './DeleteMessageModal.svelte';
  import MessageList from './MessageList.svelte';
  import {
    canManageMessage,
    cancelDeleteConfirmation,
    confirmDeleteMessage,
    createMessageActionState,
    handleEditMessage,
    handleToggleReaction,
    isMessageBusy,
    openDeleteConfirmation,
    shouldCloseDeleteOverlay,
  } from './actions';
  import {
    createViewportState,
    jumpToLatest,
    maybeLoadNewerMessages,
    maybeLoadOlderMessages,
    scrollToBottomForChannel,
    syncViewportState,
  } from './viewport';
  import { isNearBottom } from './utils';
  import { buildWindowViewModel, getCurrentServerEmojis } from './view-model';
  import type { EditMessageEventDetail, MessageEventDetail, ReactionEventDetail } from './types';

  let messagesContainer: HTMLDivElement | null = null;
  let viewportState = createViewportState();
  let actionState = createMessageActionState();
  let currentUserUuid: string | null = null;
  let viewModel: WindowViewModel = {
    currentMessages: [],
    currentChannelQuery: null,
    currentUnreadCount: 0,
    currentLastReadMessageUuid: null,
    firstNewMessageIndex: -1,
    isInitialLoading: false,
    customReactionEmojis: [],
  };

  $: currentServerEmojis = getCurrentServerEmojis(
    $activeServer?.uuid ?? null,
    $serverEmojisByServer,
  );
  $: if ($activeServer?.uuid) {
    void ensureServerEmojis($activeServer.uuid);
  }

  $: viewModel = buildWindowViewModel({
    activeChannel: $activeChannel,
    messagesByChannel: $messagesByChannel,
    channelQueryStateById: $channelQueryStateById,
    unreadCountByChannel: $unreadCountByChannel,
    lastReadMessageUuidByChannel: $lastReadMessageUuidByChannel,
    currentServerEmojis,
  });
  $: currentUserUuid = getCurrentUserUuid();

  $: if (
    $activeChannel?.uuid &&
    messagesContainer &&
    viewModel.currentMessages.length > 0 &&
    !viewModel.isInitialLoading &&
    viewportState.lastAutoScrolledChannelUuid !== $activeChannel.uuid
  ) {
    void scrollCurrentChannelToBottom($activeChannel.uuid);
  }

  $: if (
    viewportState.forceScrollToBottom &&
    $activeChannel?.uuid &&
    messagesContainer &&
    viewModel.currentMessages.length > 0 &&
    !viewModel.isInitialLoading
  ) {
    viewportState = {
      ...viewportState,
      forceScrollToBottom: false,
    };
    void scrollCurrentChannelToBottom($activeChannel.uuid);
  }

  $: if ($activeChannel?.uuid && messagesContainer) {
    const syncResult = syncViewportState({
      state: viewportState,
      activeChannelUuid: $activeChannel.uuid,
      currentMessagesLength: viewModel.currentMessages.length,
      messagesContainer,
    });

    if (syncResult.state !== viewportState) {
      viewportState = syncResult.state;
    }

    if (syncResult.shouldScrollToBottom) {
      void scrollCurrentChannelToBottom($activeChannel.uuid);
    }
  } else if (!$activeChannel?.uuid) {
    const syncResult = syncViewportState({
      state: viewportState,
      activeChannelUuid: null,
      currentMessagesLength: 0,
      messagesContainer: null,
    });
    if (syncResult.state !== viewportState) {
      viewportState = syncResult.state;
    }
  }

  function handleVisibilityChange(): void {
    if (document.visibilityState === 'visible' && $activeChannel?.uuid) {
      viewportState = {
        ...viewportState,
        forceScrollToBottom: true,
      };
    }
  }

  onMount(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange);
  });

  onDestroy(() => {
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });

  async function scrollCurrentChannelToBottom(channelUuid: string): Promise<void> {
    viewportState = await scrollToBottomForChannel({
      state: viewportState,
      activeChannelUuid: $activeChannel?.uuid ?? null,
      channelUuid,
      messagesContainer,
    });
  }

  async function handleScroll(): Promise<void> {
    if (viewportState.isPositioningAfterViewSwitch) {
      return;
    }

    if (messagesContainer) {
      viewportState = {
        ...viewportState,
        isViewportNearBottom: isNearBottom(messagesContainer),
      };
    }

    viewportState = await maybeLoadOlderMessages({
      state: viewportState,
      activeChannelUuid: $activeChannel?.uuid ?? null,
      currentChannelQuery: viewModel.currentChannelQuery,
      messagesContainer,
    });

    viewportState = await maybeLoadNewerMessages({
      state: viewportState,
      activeChannelUuid: $activeChannel?.uuid ?? null,
      currentChannelQuery: viewModel.currentChannelQuery,
      messagesContainer,
    });
  }

  async function handleJumpToLatest(): Promise<void> {
    viewportState = await jumpToLatest({
      state: viewportState,
      activeChannelUuid: $activeChannel?.uuid ?? null,
      currentChannelQuery: viewModel.currentChannelQuery,
      messagesContainer,
    });
  }

  function handleDeleteOverlayClick(event: MouseEvent): void {
    if (!shouldCloseDeleteOverlay(event)) {
      return;
    }

    actionState = cancelDeleteConfirmation(actionState);
  }

  async function onEditMessage(event: CustomEvent<EditMessageEventDetail>): Promise<void> {
    actionState = await handleEditMessage(actionState, event.detail);
  }

  function onToggleReaction(event: CustomEvent<ReactionEventDetail>): void {
    handleToggleReaction(event.detail);
  }

  function onDeleteMessage(event: CustomEvent<MessageEventDetail>): void {
    actionState = openDeleteConfirmation(actionState, event.detail);
  }

  function onCancelDelete(): void {
    actionState = cancelDeleteConfirmation(actionState);
  }

  async function onConfirmDelete(): Promise<void> {
    actionState = await confirmDeleteMessage(actionState);
  }
</script>

<section class="chat-window glass-panel" aria-label="Chat">
  <ChatHeader channelName={$activeChannel?.name ?? null} />

  <div class="chat-window-body">
    <div
      class="chat-window-messages app-scrollbar chat-messages-scroll"
      bind:this={messagesContainer}
      on:scroll={() => void handleScroll()}
    >
      <MessageList
        activeChannelName={$activeChannel?.name ?? null}
        hasActiveChannel={Boolean($activeChannel)}
        isInitialLoading={viewModel.isInitialLoading}
        currentMessages={viewModel.currentMessages}
        currentChannelQuery={viewModel.currentChannelQuery}
        firstNewMessageIndex={viewModel.firstNewMessageIndex}
        canManageMessage={(message) => canManageMessage(message, $activeServer, currentUserUuid)}
        isMessageBusy={(messageUuid) => isMessageBusy(actionState, messageUuid)}
        unicodeEmojis={UNICODE_EMOJI_PICKER}
        customReactionEmojis={viewModel.customReactionEmojis}
        on:edit={onEditMessage}
        on:delete={onDeleteMessage}
        on:toggleReaction={onToggleReaction}
      />
    </div>

    {#if $activeChannel && viewModel.currentChannelQuery?.hasMoreNewer && !viewportState.isViewportNearBottom}
      <div class="chat-window-jump">
        <button type="button" class="chat-window-jump-button" on:click={handleJumpToLatest}>
          Newer messages available
        </button>
      </div>
    {/if}

    <MessageInput />
  </div>
</section>

{#if actionState.pendingDeleteMessageUuid}
  <DeleteMessageModal
    isSubmitting={actionState.isDeleteConfirmSubmitting}
    onCancel={onCancelDelete}
    onConfirm={onConfirmDelete}
    onOverlayClick={handleDeleteOverlayClick}
  />
{/if}

<style>
  .chat-window {
    @apply flex min-w-0 flex-1 flex-col rounded-panel;
  }

  .chat-window-body {
    @apply flex min-h-0 flex-1 flex-col;
  }

  .chat-window-messages {
    @apply flex-1 overflow-auto px-4 py-4;
  }

  .chat-window-jump {
    @apply px-4 pb-2;
  }

  .chat-window-jump-button {
    @apply rounded-pill border border-accent-500/35 bg-accent-500/15 px-3 py-1 text-xs text-accent-300 transition hover:bg-accent-500/25;
  }
</style>
