<script lang="ts">
  import { Plus, Volume2 } from 'lucide-svelte';
  import { servers } from '../../lib/stores/servers';
  import { pushToast } from '../../lib/stores/toast';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import { createChannel } from './api';
  import CreateChannelModal from './CreateChannelModal.svelte';
  import { unreadCountByChannel } from '../chat/messages';
  import { DMConversationList } from '../dm';
  import type { Channel } from '../../types/gateway';

  let isCreateModalOpen = false;
  let isCreatingChannel = false;

  function selectChannel(channel: Channel): void {
    activeChannel.set(channel);
  }

  function isVoiceChannel(channel: Channel): boolean {
    const type = String(channel.channelType ?? channel.channel_type ?? '').toUpperCase();
    return type === 'VOICE';
  }

  function canCreateChannels(): boolean {
    if (!$activeServer) {
      return false;
    }
    return Boolean($activeServer.isOwner ?? $activeServer.is_owner ?? false);
  }

  async function handleCreateChannelSubmit(event: CustomEvent): Promise<void> {
    if (!$activeServer) {
      return;
    }

    isCreatingChannel = true;
    try {
      const channel = await createChannel($activeServer.uuid, {
        name: event.detail.name,
        channel_emoji: event.detail.channelEmoji || undefined,
        channel_type: event.detail.channelType,
        topic: event.detail.topic,
        is_public: event.detail.isPublic,
        allowed_roles: [],
      });

      servers.update((current) =>
        current.map((server) => {
          if (server.uuid !== $activeServer?.uuid) {
            return server;
          }
          return {
            ...server,
            channels: [...(server.channels ?? []), channel],
          };
        }),
      );

      activeServer.update((server) => {
        if (!server || server.uuid !== $activeServer?.uuid) {
          return server;
        }
        return {
          ...server,
          channels: [...(server.channels ?? []), channel],
        };
      });

      activeChannel.set(channel);
      isCreateModalOpen = false;
      pushToast({ type: 'success', message: `Channel #${channel.name} created.` });
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Failed to create channel.',
      });
    } finally {
      isCreatingChannel = false;
    }
  }
</script>

<nav class="glass-panel channel-list" aria-label="Channels">
  {#if $activeServer}
    <header class="channel-list-header">
      <span class="channel-list-title">{$activeServer.name}</span>
    </header>

    <div class="app-scrollbar channel-list-body">
      <section>
        <h3 class="channel-list-section-title">Text channels</h3>
        {#each $activeServer.channels.filter((c) => !isVoiceChannel(c)) as channel}
          <button
            type="button"
            class:channel-list-button-active={$activeChannel?.uuid === channel.uuid}
            class:channel-list-button-inactive={$activeChannel?.uuid !== channel.uuid}
            class="channel-list-button"
            on:click={() => selectChannel(channel)}
          >
            {#if channel.channelEmoji ?? channel.channel_emoji}
              <span aria-hidden="true" class="channel-list-emoji">
                {channel.channelEmoji ?? channel.channel_emoji}
              </span>
            {:else}
              <span aria-hidden="true" class="channel-list-fallback">#</span>
            {/if}
            <span class="channel-list-name">{channel.name}</span>
            {#if ($unreadCountByChannel[channel.uuid] ?? 0) > 0}
              <span class="channel-list-unread-badge">
                {$unreadCountByChannel[channel.uuid]}
              </span>
            {/if}
          </button>
        {/each}
      </section>

      <section>
        <h3 class="channel-list-section-title">Voice channels</h3>
        {#each $activeServer.channels.filter((c) => isVoiceChannel(c)) as channel}
          <button
            type="button"
            class:channel-list-button-active={$activeChannel?.uuid === channel.uuid}
            class:channel-list-button-inactive={$activeChannel?.uuid !== channel.uuid}
            class="channel-list-button"
            on:click={() => selectChannel(channel)}
          >
            <Volume2 aria-hidden="true" class="h-4 w-4 shrink-0 text-muted-500" />
            {#if channel.channelEmoji ?? channel.channel_emoji}
              <span aria-hidden="true" class="channel-list-emoji">
                {channel.channelEmoji ?? channel.channel_emoji}
              </span>
            {/if}
            <span class="channel-list-name">{channel.name}</span>
            {#if ($unreadCountByChannel[channel.uuid] ?? 0) > 0}
              <span class="channel-list-unread-badge">
                {$unreadCountByChannel[channel.uuid]}
              </span>
            {/if}
          </button>
        {/each}
      </section>
    </div>

    {#if canCreateChannels()}
      <div class="channel-list-footer">
        <button
          type="button"
          class="channel-list-button channel-list-button-inactive"
          on:click={() => {
            isCreateModalOpen = true;
          }}
          aria-label="Create channel"
          title="Create channel"
        >
          <Plus aria-hidden="true" class="h-4 w-4 shrink-0 text-muted-500" />
          <span class="channel-list-name">Create channel</span>
        </button>
      </div>
    {/if}
  {:else}
    <DMConversationList />
  {/if}
</nav>

{#if isCreateModalOpen}
  <CreateChannelModal
    isSubmitting={isCreatingChannel}
    on:close={() => {
      if (!isCreatingChannel) {
        isCreateModalOpen = false;
      }
    }}
    on:submit={handleCreateChannelSubmit}
  />
{/if}

<style>
  .channel-list {
    @apply flex w-[280px] shrink-0 flex-col overflow-hidden rounded-panel;
  }

  .channel-list-header {
    @apply flex h-16 items-center border-b border-white/10 px-4;
  }

  .channel-list-title {
    @apply truncate text-lg font-semibold text-slate-100;
  }

  .channel-list-body {
    @apply flex min-h-0 flex-1 flex-col gap-5 overflow-auto px-3 py-3;
  }

  .channel-list-section-title {
    @apply mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-500;
  }

  .channel-list-button {
    @apply mb-0.5 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition;
  }

  .channel-list-button-active {
    @apply bg-white/10 text-slate-100;
  }

  .channel-list-button-inactive {
    @apply text-muted-300 hover:bg-white/5 hover:text-slate-100;
  }

  .channel-list-emoji {
    @apply text-muted-400;
  }

  .channel-list-fallback {
    @apply text-muted-500;
  }

  .channel-list-name {
    @apply truncate font-medium;
  }

  .channel-list-unread-badge {
    @apply ml-auto rounded-pill bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200;
  }

  .channel-list-footer {
    @apply mt-auto border-t border-white/10 px-3 py-3;
  }
</style>
