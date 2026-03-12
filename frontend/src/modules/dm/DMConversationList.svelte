<script lang="ts">
  import { onMount } from 'svelte';
  import { Check, MessageSquarePlus, UserMinus, X } from 'lucide-svelte';
  import { joinGatewayDMConversation } from '../../lib/socket';
  import { pushToast } from '../../lib/stores/toast';
  import { activeDMConversation } from '../../lib/stores/ui';
  import CreateDMConversationModal from './CreateDMConversationModal.svelte';
  import {
    createDMConversation,
    dmConversations,
    ensureDMConversations,
    ensureDMMessages,
    openDirectConversation,
  } from './dm.store';
  import {
    acceptFriendRequest,
    declineFriendRequest,
    friends,
    friendsError,
    friendsLoading,
    incomingFriendRequests,
    loadFriendsData,
    outgoingFriendRequests,
    removeFriendRelation,
  } from './friends.store';
  import type { DMConversation, FriendUser } from '../../types/gateway';

  let isLoading = false;
  let isCreateModalOpen = false;
  let isCreatingConversation = false;

  async function loadConversations(): Promise<void> {
    isLoading = true;
    try {
      await Promise.all([ensureDMConversations(), loadFriendsData()]);
      if (!$activeDMConversation && $dmConversations.length > 0) {
        activeDMConversation.set($dmConversations[0] ?? null);
      }
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to load direct messages.',
      });
    } finally {
      isLoading = false;
    }
  }

  function selectConversation(conversation: DMConversation): void {
    activeDMConversation.set(conversation);
  }

  function conversationName(conversation: DMConversation): string {
    if (conversation.title) {
      return conversation.title;
    }

    const others = conversation.participants ?? [];
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
  $: offlineFriends = $friends.filter((friend) => !Boolean(friend.isOnline ?? friend.is_online));

  onMount(() => {
    void loadConversations();
  });
</script>

<nav class="flex min-h-0 flex-1 flex-col" aria-label="Direct messages">
  <header class="flex items-center justify-between px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-muted-500">
    <span>Direct messages</span>
    <button
      type="button"
      class="rounded-md p-1 text-muted-400 transition hover:bg-white/10 hover:text-slate-100"
      title="New conversation"
      aria-label="New conversation"
      on:click={() => {
        isCreateModalOpen = true;
      }}
    >
      <MessageSquarePlus class="h-4 w-4" />
    </button>
  </header>

  <div class="app-scrollbar min-h-0 flex-1 overflow-auto px-3 pb-3">
    {#if isLoading || $friendsLoading}
      <p class="px-2 py-2 text-sm text-muted-300">Loading...</p>
    {:else}
      <section class="mb-4">
        <h3 class="mb-1 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500">Friends</h3>

        {#if onlineFriends.length > 0}
          <p class="px-2 pb-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/80">Online</p>
          {#each onlineFriends as friend (friend.uuid)}
            <button
              type="button"
              class="mb-1 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm text-muted-100 transition hover:bg-white/5"
              on:click={() => startDirectConversation(friend)}
            >
              <div class="h-8 w-8 shrink-0 overflow-hidden rounded-full bg-surface-800">
                {#if friend.avatarUrl ?? friend.avatar_url}
                  <img src={friend.avatarUrl ?? friend.avatar_url} alt={friend.displayName ?? friend.display_name ?? friend.email} class="h-full w-full object-cover" />
                {/if}
              </div>
              <span class="truncate">{friend.displayName ?? friend.display_name ?? friend.email}</span>
            </button>
          {/each}
        {/if}

        {#if offlineFriends.length > 0}
          <p class="px-2 pb-1 pt-1 text-[10px] uppercase tracking-[0.16em] text-muted-500">Offline</p>
          {#each offlineFriends as friend (friend.uuid)}
            <div class="mb-1 flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-muted-300">
              <div class="h-8 w-8 shrink-0 overflow-hidden rounded-full bg-surface-800">
                {#if friend.avatarUrl ?? friend.avatar_url}
                  <img src={friend.avatarUrl ?? friend.avatar_url} alt={friend.displayName ?? friend.display_name ?? friend.email} class="h-full w-full object-cover" />
                {/if}
              </div>
              <span class="truncate">{friend.displayName ?? friend.display_name ?? friend.email}</span>
              <button
                type="button"
                class="ml-auto rounded p-1 text-muted-400 transition hover:bg-white/10 hover:text-slate-100"
                title="Remove friend"
                on:click={() => removeRelation(friend.relationUuid ?? friend.relation_uuid ?? '')}
              >
                <UserMinus class="h-4 w-4" />
              </button>
            </div>
          {/each}
        {/if}

        {#if onlineFriends.length === 0 && offlineFriends.length === 0}
          <p class="px-2 py-2 text-sm text-muted-300">No friends yet.</p>
        {/if}
      </section>

      <section class="mb-4">
        <h3 class="mb-1 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500">Pending</h3>

        {#if $incomingFriendRequests.length === 0 && $outgoingFriendRequests.length === 0}
          <p class="px-2 py-2 text-sm text-muted-300">No pending requests.</p>
        {/if}

        {#if $incomingFriendRequests.length > 0}
          <p class="px-2 pb-1 text-[10px] uppercase tracking-[0.16em] text-emerald-300/80">Incoming</p>
          {#each $incomingFriendRequests as request (request.uuid)}
            <div class="mb-1 flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-slate-100">
              <span class="truncate">{request.user.displayName ?? request.user.display_name ?? request.user.email}</span>
              <button
                type="button"
                class="ml-auto rounded p-1 text-emerald-300 transition hover:bg-emerald-500/15"
                on:click={() => acceptRequest(request.uuid)}
                title="Accept"
              >
                <Check class="h-4 w-4" />
              </button>
              <button
                type="button"
                class="rounded p-1 text-red-300 transition hover:bg-red-500/15"
                on:click={() => declineRequest(request.uuid)}
                title="Decline"
              >
                <X class="h-4 w-4" />
              </button>
            </div>
          {/each}
        {/if}

        {#if $outgoingFriendRequests.length > 0}
          <p class="px-2 pb-1 pt-1 text-[10px] uppercase tracking-[0.16em] text-muted-500">Outgoing</p>
          {#each $outgoingFriendRequests as request (request.uuid)}
            <div class="mb-1 flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-muted-300">
              <span class="truncate">{request.user.displayName ?? request.user.display_name ?? request.user.email}</span>
              <button
                type="button"
                class="ml-auto rounded p-1 text-muted-300 transition hover:bg-white/10 hover:text-slate-100"
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
        <h3 class="mb-1 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-500">Direct Messages</h3>
        {#if $dmConversations.length === 0}
          <p class="px-2 py-2 text-sm text-muted-300">No direct messages yet.</p>
        {:else}
          {#each $dmConversations as conversation (conversation.uuid)}
            <button
              type="button"
              class={`mb-1 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition ${
                $activeDMConversation?.uuid === conversation.uuid
                  ? 'bg-white/10 text-slate-100'
                  : 'text-muted-300 hover:bg-white/5 hover:text-slate-100'
              }`}
              on:click={() => selectConversation(conversation)}
            >
              <div class="h-8 w-8 shrink-0 overflow-hidden rounded-full bg-surface-800">
                {#if conversation.avatarUrl ?? conversation.avatar_url}
                  <img
                    src={conversation.avatarUrl ?? conversation.avatar_url}
                    alt={conversationName(conversation)}
                    class="h-full w-full object-cover"
                  />
                {/if}
              </div>
              <span class="truncate font-medium">{conversationName(conversation)}</span>
              {#if unreadCount(conversation) > 0}
                <span class="ml-auto rounded-pill bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200">
                  {unreadCount(conversation)}
                </span>
              {/if}
            </button>
          {/each}
        {/if}
      </section>

      {#if $friendsError}
        <p class="mt-3 px-2 text-xs text-red-300">{$friendsError}</p>
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
