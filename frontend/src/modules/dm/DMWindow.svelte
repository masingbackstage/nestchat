<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { Bell, MessagesSquare, Search, Users } from 'lucide-svelte';
  import { getCurrentUserUuid } from '../../lib/auth';
  import { pushToast } from '../../lib/stores/toast';
  import { activeDMConversation } from '../../lib/stores/ui';
  import {
    clearDMUnread,
    dmMessagesByConversation,
    dmQueryStateByConversation,
    ensureDMMessages,
    loadNewerDMMessages,
    loadOlderDMMessages,
    markDMConversationAsRead,
  } from './dm.store';
  import { sendDeleteDMMessage, sendEditDMMessage, sendToggleDMReaction } from '../../lib/socket';
  import MessageItem from '../chat/message-item';
  import DMMessageInput from './DMMessageInput.svelte';

  let messagesContainer: HTMLDivElement | null = null;
  let currentUserUuid: string | null = null;

  $: conversationUuid = $activeDMConversation?.uuid ?? null;
  $: currentMessages = conversationUuid ? ($dmMessagesByConversation[conversationUuid] ?? []) : [];
  $: queryState = conversationUuid ? $dmQueryStateByConversation[conversationUuid] : null;
  $: currentUserUuid = getCurrentUserUuid();

  $: if (conversationUuid) {
    void ensureDMMessages(conversationUuid);
  }

  $: if (conversationUuid && currentMessages.length > 0) {
    clearDMUnread(conversationUuid);
    void markDMConversationAsRead(conversationUuid, currentMessages[currentMessages.length - 1]?.uuid);
  }

  onMount(async () => {
    await tick();
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  });

  function conversationTitle(): string {
    if ($activeDMConversation?.title) {
      return $activeDMConversation.title;
    }

    const others = ($activeDMConversation?.participants ?? []).filter(
      (participant) => participant.uuid !== currentUserUuid,
    );
    if (others.length === 0) {
      return 'Direct message';
    }

    return others.map((participant) => participant.displayName ?? participant.display_name ?? 'Unknown').join(', ');
  }

  function canManageMessage(message: { author_uuid?: string; is_deleted?: boolean }): boolean {
    if (message.is_deleted) {
      return false;
    }
    return Boolean(currentUserUuid && message.author_uuid === currentUserUuid);
  }

  async function handleEditMessage(event: CustomEvent<{ messageUuid: string; content: string }>): Promise<void> {
    const sent = sendEditDMMessage(event.detail.messageUuid, event.detail.content);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    }
  }

  function handleDeleteMessage(event: CustomEvent<{ messageUuid: string }>): void {
    const sent = sendDeleteDMMessage(event.detail.messageUuid);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    }
  }

  function handleToggleReaction(event: CustomEvent<{ messageUuid: string; emoji: string }>): void {
    const sent = sendToggleDMReaction(event.detail.messageUuid, event.detail.emoji);
    if (!sent) {
      pushToast({ type: 'error', message: 'Gateway connection is unavailable.' });
    }
  }

  async function handleScroll(): Promise<void> {
    if (!conversationUuid || !messagesContainer || !queryState) {
      return;
    }

    if (messagesContainer.scrollTop <= 36 && queryState.hasMoreOlder && !queryState.isLoadingOlder) {
      const previousScrollHeight = messagesContainer.scrollHeight;
      await loadOlderDMMessages(conversationUuid);
      await tick();
      if (messagesContainer) {
        const delta = messagesContainer.scrollHeight - previousScrollHeight;
        messagesContainer.scrollTop += Math.max(0, delta);
      }
    }

    const distanceFromBottom =
      messagesContainer.scrollHeight - (messagesContainer.scrollTop + messagesContainer.clientHeight);
    if (distanceFromBottom <= 80 && queryState.hasMoreNewer && !queryState.isLoadingNewer) {
      await loadNewerDMMessages(conversationUuid);
    }
  }
</script>

<section class="glass-panel flex min-w-0 flex-1 flex-col rounded-panel" aria-label="Direct messages">
  <header class="flex h-16 items-center border-b border-white/10 px-5">
    {#if $activeDMConversation}
      <MessagesSquare class="h-5 w-5 text-muted-400" aria-hidden="true" />
      <h2 class="truncate text-lg font-semibold text-slate-100">{conversationTitle()}</h2>
    {:else}
      <h2 class="text-lg font-semibold text-slate-100">Select a conversation</h2>
    {/if}

    <div class="ml-auto hidden items-center gap-4 text-muted-300 md:flex">
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Notifications">
        <Bell class="h-4 w-4" />
      </button>
      <button type="button" class="rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100" aria-label="Members">
        <Users class="h-4 w-4" />
      </button>
      <div class="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5">
        <input type="text" readonly value="" placeholder="Search" class="w-24 bg-transparent text-xs text-muted-200 outline-none placeholder:text-muted-500" />
        <Search class="h-3.5 w-3.5 text-muted-400" />
      </div>
    </div>
  </header>

  <div class="flex min-h-0 flex-1 flex-col">
    <div class="app-scrollbar chat-messages-scroll flex-1 space-y-1 overflow-auto px-4 py-4" bind:this={messagesContainer} on:scroll={handleScroll}>
      {#if !$activeDMConversation}
        <p class="text-sm text-muted-300">Select or create a direct message to start chatting.</p>
      {:else if queryState?.isLoadingInitial && currentMessages.length === 0}
        <p class="text-sm text-muted-300">Loading messages...</p>
      {:else if currentMessages.length === 0}
        <p class="text-sm text-muted-300">No messages yet. Start the conversation.</p>
      {:else}
        {#each currentMessages as message (message.uuid)}
          <MessageItem
            {message}
            canManage={canManageMessage(message)}
            isBusy={false}
            on:edit={handleEditMessage}
            on:delete={handleDeleteMessage}
            on:toggleReaction={handleToggleReaction}
          />
        {/each}
      {/if}
    </div>

    <DMMessageInput conversation={$activeDMConversation} />
  </div>
</section>
