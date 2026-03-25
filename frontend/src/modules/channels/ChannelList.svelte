<script lang="ts">
  import { MicOff, Plus, Volume2 } from 'lucide-svelte';
  import { servers } from '../../lib/stores/servers';
  import { pushToast } from '../../lib/stores/toast';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import { createChannel } from './api';
  import CreateChannelModal from './CreateChannelModal.svelte';
  import { unreadCountByChannel } from '../chat/messages';
  import { DMConversationList } from '../dm';
  import type { Channel, VoiceOccupant } from '../../types/gateway';
  import { joinVoiceCall } from '../voice/store';
  import { voiceOccupantsByChannel } from '../voice/occupancy';

  let isCreateModalOpen = false;
  let isCreatingChannel = false;

  function selectChannel(channel: Channel): void {
    activeChannel.set(channel);
    if (!$activeServer) {
      return;
    }
    if (isVoiceChannel(channel)) {
      void joinVoiceCall($activeServer.uuid, channel.uuid, channel.name);
    }
  }

  function isVoiceChannel(channel: Channel): boolean {
    const type = String(channel.channelType ?? channel.channel_type ?? '').toUpperCase();
    return type === 'VOICE';
  }

  function getVoiceOccupants(channel: Channel): VoiceOccupant[] {
    return (
      $voiceOccupantsByChannel[channel.uuid] ??
      channel.voiceOccupants ??
      channel.voice_occupants ??
      []
    );
  }

  function getOccupantDisplayName(occupant: VoiceOccupant): string {
    return occupant.displayName ?? occupant.display_name ?? 'Unknown user';
  }

  function getOccupantAvatarUrl(occupant: VoiceOccupant): string | null {
    return occupant.avatarUrl ?? occupant.avatar_url ?? null;
  }

  function getOccupantInitials(occupant: VoiceOccupant): string {
    return getOccupantDisplayName(occupant).slice(0, 2).toUpperCase();
  }

  function isOccupantSpeaking(occupant: VoiceOccupant): boolean {
    return Boolean(occupant.isSpeaking ?? occupant.is_speaking ?? false);
  }

  function isOccupantMuted(occupant: VoiceOccupant): boolean {
    return Boolean(occupant.isMuted ?? occupant.is_muted ?? false);
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
          <div class="channel-list-voice-channel">
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

            {#if getVoiceOccupants(channel).length > 0}
              <div class="channel-list-voice-occupants">
                {#each getVoiceOccupants(channel) as occupant}
                  <div
                    class:channel-list-voice-occupant-speaking={isOccupantSpeaking(occupant)}
                    class="channel-list-voice-occupant"
                  >
                    {#if getOccupantAvatarUrl(occupant)}
                      <img
                        class:channel-list-voice-avatar-speaking={isOccupantSpeaking(occupant)}
                        class="channel-list-voice-avatar"
                        src={getOccupantAvatarUrl(occupant)}
                        alt={getOccupantDisplayName(occupant)}
                      />
                    {:else}
                      <div
                        class:channel-list-voice-avatar-speaking={isOccupantSpeaking(occupant)}
                        class="channel-list-voice-avatar channel-list-voice-avatar-fallback"
                      >
                        {getOccupantInitials(occupant)}
                      </div>
                    {/if}
                    <span class="channel-list-voice-occupant-name">
                      {getOccupantDisplayName(occupant)}
                    </span>
                    {#if isOccupantMuted(occupant)}
                      <span
                        class="channel-list-voice-occupant-muted"
                        aria-label={`${getOccupantDisplayName(occupant)} is muted`}
                      >
                        <MicOff aria-hidden="true" class="h-3.5 w-3.5" />
                      </span>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
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

  .channel-list-voice-channel {
    @apply mb-2;
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

  .channel-list-voice-occupants {
    @apply ml-7 mt-1.5 space-y-1;
  }

  .channel-list-voice-occupant {
    @apply flex items-center gap-2 rounded-lg px-2 py-1 text-xs text-muted-300;
  }

  .channel-list-voice-occupant-speaking {
    @apply bg-emerald-500/10 text-emerald-100;
  }

  .channel-list-voice-avatar {
    @apply h-5 w-5 rounded-md object-cover transition;
  }

  .channel-list-voice-avatar-speaking {
    @apply ring-2 ring-emerald-400/70;
  }

  .channel-list-voice-avatar-fallback {
    @apply flex items-center justify-center bg-white/10 text-[10px] font-semibold text-slate-100;
  }

  .channel-list-voice-occupant-name {
    @apply truncate;
  }

  .channel-list-voice-occupant-muted {
    @apply ml-auto h-3.5 w-3.5 shrink-0 text-rose-300/90;
  }

  .channel-list-footer {
    @apply mt-auto border-t border-white/10 px-3 py-3;
  }
</style>
