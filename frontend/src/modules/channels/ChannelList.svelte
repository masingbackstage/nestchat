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

<nav
  class="glass-panel w-[280px] shrink-0 rounded-panel"
  aria-label="Channels"
>
  {#if $activeServer}
    <header class="flex h-16 items-center justify-between border-b border-white/10 px-4">
      <span class="truncate text-lg font-semibold text-slate-100">{$activeServer.name}</span>
      {#if canCreateChannels()}
        <button
          type="button"
          class="ml-2 rounded-xl border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-medium text-muted-200 transition hover:border-glass-highlight hover:bg-white/10 hover:text-slate-100"
          on:click={() => {
            isCreateModalOpen = true;
          }}
          aria-label="Create channel"
          title="Create channel"
        >
          +
        </button>
      {/if}
    </header>

    <div class="app-scrollbar flex min-h-0 flex-1 flex-col gap-5 overflow-auto px-3 py-3">
      <section>
        <h3 class="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-500">
          Text channels
        </h3>
        {#each $activeServer.channels.filter((c) => !isVoiceChannel(c)) as channel}
          <button
            type="button"
            class={`mb-0.5 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition ${
              $activeChannel?.uuid === channel.uuid
                ? 'bg-white/10 text-slate-100'
                : 'text-muted-300 hover:bg-white/5 hover:text-slate-100'
            }`}
            on:click={() => selectChannel(channel)}
          >
            <span aria-hidden="true" class="text-muted-500">#</span>
            <span class="truncate font-medium">{channel.name}</span>
            {#if ($unreadCountByChannel[channel.uuid] ?? 0) > 0}
              <span
                class="ml-auto rounded-pill bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200"
              >
                {$unreadCountByChannel[channel.uuid]}
              </span>
            {/if}
          </button>
        {/each}
      </section>

      <section>
        <h3 class="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-500">
          Voice channels
        </h3>
        {#each $activeServer.channels.filter((c) => isVoiceChannel(c)) as channel}
          <button
            type="button"
            class={`mb-0.5 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition ${
              $activeChannel?.uuid === channel.uuid
                ? 'bg-white/10 text-slate-100'
                : 'text-muted-300 hover:bg-white/5 hover:text-slate-100'
            }`}
            on:click={() => selectChannel(channel)}
          >
            <Volume2 aria-hidden="true" class="h-4 w-4 shrink-0 text-muted-500" />
            <span class="truncate font-medium">{channel.name}</span>
            {#if ($unreadCountByChannel[channel.uuid] ?? 0) > 0}
              <span
                class="ml-auto rounded-pill bg-emerald-500/20 px-2 py-0.5 text-[11px] font-semibold text-emerald-200"
              >
                {$unreadCountByChannel[channel.uuid]}
              </span>
            {/if}
          </button>
        {/each}
      </section>
    </div>
  {:else}
    <div class="p-4 text-sm text-muted-300">No server selected</div>
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
