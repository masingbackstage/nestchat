<script lang="ts">
  import { Volume2 } from 'lucide-svelte';
  import { servers } from '../../lib/stores/servers';
  import { pushToast } from '../../lib/stores/toast';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import { createChannel } from './channels.api';
  import CreateChannelModal from './CreateChannelModal.svelte';
  import { unreadCountByChannel } from '../chat/messages.store';
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
      pushToast({ type: 'success', message: `Utworzono kanał #${channel.name}.` });
    } catch (error) {
      pushToast({
        type: 'error',
        message: error instanceof Error ? error.message : 'Nie udało się utworzyć kanału.',
      });
    } finally {
      isCreatingChannel = false;
    }
  }
</script>

<nav
  class="flex w-[260px] shrink-0 flex-col border-r border-slate-800 bg-app-900"
  aria-label="Channels"
>
  {#if $activeServer}
    <header
      class="flex h-12 items-center justify-between border-b border-slate-800 px-3.5 text-sm font-bold text-white"
    >
      <span class="truncate">{$activeServer.name}</span>
      {#if canCreateChannels()}
        <button
          type="button"
          class="ml-2 rounded border border-slate-700 px-2 py-0.5 text-xs text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
          on:click={() => {
            isCreateModalOpen = true;
          }}
          aria-label="Utwórz kanał"
          title="Utwórz kanał"
        >
          +
        </button>
      {/if}
    </header>

    <div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto p-2">
      {#each $activeServer.channels as channel}
        <button
          type="button"
          class={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors ${
            $activeChannel?.uuid === channel.uuid
              ? 'bg-slate-700 text-white'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
          on:click={() => selectChannel(channel)}
        >
          {#if isVoiceChannel(channel)}
            <Volume2 aria-hidden="true" class="h-4 w-4 shrink-0 text-slate-500" />
          {:else}
            <span aria-hidden="true" class="text-slate-500">#</span>
          {/if}
          <span class="truncate">{channel.name}</span>
          {#if ($unreadCountByChannel[channel.uuid] ?? 0) > 0}
            <span
              class="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200"
            >
              {$unreadCountByChannel[channel.uuid]}
            </span>
          {/if}
        </button>
      {/each}
    </div>
  {:else}
    <div class="p-4 text-sm text-slate-400">Brak wybranego serwera</div>
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
