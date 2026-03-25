<script lang="ts">
  import { onMount } from 'svelte';
  import { Check, MessageSquarePlus, UserMinus, X } from 'lucide-svelte';
  import { getCurrentUserUuid } from '../../../lib/auth';
  import { joinGatewayDMConversation } from '../../../lib/socket';
  import { pushToast } from '../../../lib/stores/toast';
  import { activeDMConversation } from '../../../lib/stores/ui';
  import CreateDMConversationModal from './CreateDMConversationModal.svelte';
  import {
    createDMConversation,
    dmConversations,
    dmConversationsLoading,
    dmConversationsRefreshing,
    dmStorageHydrated,
    ensureDMConversations,
    ensureDMMessages,
    openDirectConversation,
  } from '../messages';
  import {
    acceptFriendRequest,
    declineFriendRequest,
    friends,
    friendsError,
    friendsLoading,
    friendsRefreshing,
    friendsStorageHydrated,
    incomingFriendRequests,
    loadFriendsData,
    outgoingFriendRequests,
    removeFriendRelation,
  } from '../friends';
  import { loadDMUICache } from '../storage';
  import type { DMConversation, FriendUser } from '../../../types/gateway';

  let isCreateModalOpen = false;
  let isCreatingConversation = false;
  let currentUserUuid: string | null = null;

  async function loadConversations(): Promise<void> {
    try {
      await Promise.all([ensureDMConversations(), loadFriendsData()]);
      if (!$activeDMConversation && $dmConversations.length > 0) {
        const cachedActiveConversationUuid = loadDMUICache().activeConversationUuid;
        const cachedActiveConversation =
          $dmConversations.find((conversation) => conversation.uuid === cachedActiveConversationUuid) ??
          null;
        activeDMConversation.set(cachedActiveConversation ?? $dmConversations[0] ?? null);
      }
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load direct messages.',
      });
    } finally {
      // no-op: loading state is owned by the stores
    }
  }

  function selectConversation(conversation: DMConversation): void {
    activeDMConversation.set(conversation);
  }

  function conversationName(conversation: DMConversation): string {
    if (conversation.title) {
      return conversation.title;
    }

    const others = (conversation.participants ?? []).filter(
      (participant) => participant.uuid !== currentUserUuid,
    );
    if (others.length === 0) {
      return 'Direct message';
    }
    return others
      .map((participant) => participant.displayName ?? participant.display_name ?? 'Unknown')
      .join(', ');
  }

  function unreadCount(conversation: DMConversation): number {
    return Number(conversation.unreadCount ?? conversation.unread_count ?? 0);
  }

  async function handleCreateConversation(
    event: CustomEvent<{ participantUuids: string[]; title?: string }>,
  ): Promise<void> {
    isCreatingConversation = true;
    try {
      const created = await createDMConversation(event.detail.participantUuids, event.detail.title);
      activeDMConversation.set(created);
      await ensureDMMessages(created.uuid);
      joinGatewayDMConversation(created.uuid);
      isCreateModalOpen = false;
      pushToast({ type: 'success', message: 'Conversation created.' });
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to create conversation.',
      });
    } finally {
      isCreatingConversation = false;
    }
  }

  async function startDirectConversation(friend: FriendUser): Promise<void> {
    try {
      const conversation = await openDirectConversation(friend.uuid);
      await ensureDMMessages(conversation.uuid);
      joinGatewayDMConversation(conversation.uuid);
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to open direct conversation.',
      });
    }
  }

  async function acceptRequest(requestUuid: string): Promise<void> {
    try {
      await acceptFriendRequest(requestUuid);
      pushToast({ type: 'success', message: 'Friend request accepted.' });
    } catch (error) {
      pushToast({ type: 'error', message: error instanceof Error ? error.message : 'Failed to accept request.' });
    }
  }

  async function declineRequest(requestUuid: string): Promise<void> {
    try {
      await declineFriendRequest(requestUuid);
      pushToast({ type: 'success', message: 'Friend request declined.' });
    } catch (error) {
      pushToast({ type: 'error', message: error instanceof Error ? error.message : 'Failed to decline request.' });
    }
  }

  async function removeRelation(relationUuid: string): Promise<void> {
    if (!relationUuid) {
      return;
    }
    try {
      await removeFriendRelation(relationUuid);
      pushToast({ type: 'success', message: 'Relation removed.' });
    } catch (error) {
      pushToast({ type: 'error', message: error instanceof Error ? error.message : 'Failed to remove relation.' });
    }
  }

  $: onlineFriends = $friends.filter((friend) => Boolean(friend.isOnline ?? friend.is_online));
  $: offlineFriends = $friends.filter((friend) => !(friend.isOnline ?? friend.is_online));
  $: currentUserUuid = getCurrentUserUuid();

  onMount(() => {
    void loadConversations();
  });
</script>

<nav class="flex min-h-0 flex-1 flex-col" aria-label="Direct messages">
  <header class="dm-conversation-list-header">
    <span>Direct messages</span>
    <button
      type="button"
      class="dm-conversation-list-header-button"
      title="New conversation"
      aria-label="New conversation"
      on:click={() => {
        isCreateModalOpen = true;
      }}
    >
      <MessageSquarePlus class="h-4 w-4" />
    </button>
  </header>

  <div class="app-scrollbar dm-conversation-list-body">
    {#if ($dmConversationsLoading && !$dmStorageHydrated) || ($friendsLoading && !$friendsStorageHydrated)}
      <p class="dm-conversation-list-state-copy">Loading...</p>
    {:else}
      {#if $dmConversationsRefreshing || $friendsRefreshing}
        <p class="dm-conversation-list-refresh-copy">Refreshing...</p>
      {/if}
      <section class="dm-conversation-list-section">
        <h3 class="dm-conversation-list-section-title">Friends</h3>

        {#if onlineFriends.length > 0}
          <p class="dm-conversation-list-subsection dm-conversation-list-subsection-online">Online</p>
          {#each onlineFriends as friend (friend.uuid)}
            <button
              type="button"
              class="dm-conversation-list-row dm-conversation-list-row-button dm-conversation-list-row-online"
              on:click={() => startDirectConversation(friend)}
            >
              <div class="dm-conversation-list-avatar">
                {#if friend.avatarUrl ?? friend.avatar_url}
                  <img src={friend.avatarUrl ?? friend.avatar_url} alt={friend.displayName ?? friend.display_name ?? friend.email} class="dm-conversation-list-avatar-image" />
                {/if}
              </div>
              <span class="dm-conversation-list-name">{friend.displayName ?? friend.display_name ?? friend.email}</span>
            </button>
          {/each}
        {/if}

        {#if offlineFriends.length > 0}
          <p class="dm-conversation-list-subsection dm-conversation-list-subsection-muted">Offline</p>
          {#each offlineFriends as friend (friend.uuid)}
            <div class="dm-conversation-list-row dm-conversation-list-row-muted">
              <div class="dm-conversation-list-avatar">
                {#if friend.avatarUrl ?? friend.avatar_url}
                  <img src={friend.avatarUrl ?? friend.avatar_url} alt={friend.displayName ?? friend.display_name ?? friend.email} class="dm-conversation-list-avatar-image" />
                {/if}
              </div>
              <span class="dm-conversation-list-name">{friend.displayName ?? friend.display_name ?? friend.email}</span>
              <button
                type="button"
                class="dm-conversation-list-inline-button dm-conversation-list-inline-button-muted"
                title="Remove friend"
                on:click={() => removeRelation(friend.relationUuid ?? friend.relation_uuid ?? '')}
              >
                <UserMinus class="h-4 w-4" />
              </button>
            </div>
          {/each}
        {/if}

        {#if onlineFriends.length === 0 && offlineFriends.length === 0}
          <p class="dm-conversation-list-state-copy">No friends yet.</p>
        {/if}
      </section>

      <section class="dm-conversation-list-section">
        <h3 class="dm-conversation-list-section-title">Pending</h3>

        {#if $incomingFriendRequests.length === 0 && $outgoingFriendRequests.length === 0}
          <p class="dm-conversation-list-state-copy">No pending requests.</p>
        {/if}

        {#if $incomingFriendRequests.length > 0}
          <p class="dm-conversation-list-subsection dm-conversation-list-subsection-online">Incoming</p>
          {#each $incomingFriendRequests as request (request.uuid)}
            <div class="dm-conversation-list-row dm-conversation-list-row-default">
              <span class="dm-conversation-list-name">{request.user.displayName ?? request.user.display_name ?? request.user.email}</span>
              <button
                type="button"
                class="dm-conversation-list-inline-button dm-conversation-list-inline-button-success"
                on:click={() => acceptRequest(request.uuid)}
                title="Accept"
              >
                <Check class="h-4 w-4" />
              </button>
              <button
                type="button"
                class="dm-conversation-list-inline-button dm-conversation-list-inline-button-danger"
                on:click={() => declineRequest(request.uuid)}
                title="Decline"
              >
                <X class="h-4 w-4" />
              </button>
            </div>
          {/each}
        {/if}

        {#if $outgoingFriendRequests.length > 0}
          <p class="dm-conversation-list-subsection dm-conversation-list-subsection-muted">Outgoing</p>
          {#each $outgoingFriendRequests as request (request.uuid)}
            <div class="dm-conversation-list-row dm-conversation-list-row-muted">
              <span class="dm-conversation-list-name">{request.user.displayName ?? request.user.display_name ?? request.user.email}</span>
              <button
                type="button"
                class="dm-conversation-list-inline-button dm-conversation-list-inline-button-muted"
                on:click={() => removeRelation(request.uuid)}
                title="Cancel request"
              >
                <X class="h-4 w-4" />
              </button>
            </div>
          {/each}
        {/if}
      </section>

      <section>
        <h3 class="dm-conversation-list-section-title">Direct Messages</h3>
        {#if $dmConversations.length === 0}
          <p class="dm-conversation-list-state-copy">No direct messages yet.</p>
        {:else}
          {#each $dmConversations as conversation (conversation.uuid)}
            <button
              type="button"
              class:dm-conversation-list-conversation-active={$activeDMConversation?.uuid === conversation.uuid}
              class:dm-conversation-list-conversation-inactive={$activeDMConversation?.uuid !== conversation.uuid}
              class="dm-conversation-list-row dm-conversation-list-row-button"
              on:click={() => selectConversation(conversation)}
            >
              <div class="dm-conversation-list-avatar">
                {#if conversation.avatarUrl ?? conversation.avatar_url}
                  <img
                    src={conversation.avatarUrl ?? conversation.avatar_url}
                    alt={conversationName(conversation)}
                    class="dm-conversation-list-avatar-image"
                  />
                {/if}
              </div>
              <span class="dm-conversation-list-name dm-conversation-list-name-strong">{conversationName(conversation)}</span>
              {#if unreadCount(conversation) > 0}
                <span class="dm-conversation-list-unread-badge">
                  {unreadCount(conversation)}
                </span>
              {/if}
            </button>
          {/each}
        {/if}
      </section>

      {#if $friendsError}
        <p class="dm-conversation-list-error">{$friendsError}</p>
      {/if}
    {/if}
  </div>
</nav>

{#if isCreateModalOpen}
  <CreateDMConversationModal
    isSubmitting={isCreatingConversation}
    on:close={() => {
      if (!isCreatingConversation) {
        isCreateModalOpen = false;
      }
    }}
    on:submit={handleCreateConversation}
  />
{/if}

<style>
  .dm-conversation-list-header {
    @apply flex items-center justify-between px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-500;
  }

  .dm-conversation-list-header-button {
    @apply rounded-md p-1 text-muted-400 transition hover:bg-white/10 hover:text-slate-100;
  }

  .dm-conversation-list-body {
    @apply min-h-0 flex-1 overflow-auto px-3 pb-3;
  }

  .dm-conversation-list-section {
    @apply mb-4;
  }

  .dm-conversation-list-section-title {
    @apply mb-1 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500;
  }

  .dm-conversation-list-subsection {
    @apply px-2 pb-1 text-[10px] uppercase tracking-[0.16em];
  }

  .dm-conversation-list-subsection-online {
    @apply text-emerald-300/80;
  }

  .dm-conversation-list-subsection-muted {
    @apply pt-1 text-muted-500;
  }

  .dm-conversation-list-state-copy {
    @apply px-2 py-2 text-sm text-muted-300;
  }

  .dm-conversation-list-refresh-copy {
    @apply px-2 pb-2 text-[11px] uppercase tracking-[0.16em] text-muted-500;
  }

  .dm-conversation-list-row {
    @apply mb-1 flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm;
  }

  .dm-conversation-list-row-button {
    @apply w-full text-left transition;
  }

  .dm-conversation-list-row-online {
    @apply text-muted-100 hover:bg-white/5;
  }

  .dm-conversation-list-row-muted {
    @apply text-muted-300;
  }

  .dm-conversation-list-row-default {
    @apply text-slate-100;
  }

  .dm-conversation-list-conversation-active {
    @apply bg-white/10 text-slate-100;
  }

  .dm-conversation-list-conversation-inactive {
    @apply text-muted-300 hover:bg-white/5 hover:text-slate-100;
  }

  .dm-conversation-list-avatar {
    @apply h-8 w-8 shrink-0 overflow-hidden rounded-full bg-surface-800;
  }

  .dm-conversation-list-avatar-image {
    @apply h-full w-full object-cover;
  }

  .dm-conversation-list-name {
    @apply truncate;
  }

  .dm-conversation-list-name-strong {
    @apply font-medium;
  }

  .dm-conversation-list-inline-button {
    @apply ml-auto rounded p-1 transition;
  }

  .dm-conversation-list-inline-button-success {
    @apply text-emerald-300 hover:bg-emerald-500/15;
  }

  .dm-conversation-list-inline-button-danger {
    @apply text-red-300 hover:bg-red-500/15;
  }

  .dm-conversation-list-inline-button-muted {
    @apply text-muted-300 hover:bg-white/10 hover:text-slate-100;
  }

  .dm-conversation-list-unread-badge {
    @apply ml-auto rounded-pill bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200;
  }

  .dm-conversation-list-error {
    @apply mt-3 px-2 text-xs text-red-300;
  }
</style>
