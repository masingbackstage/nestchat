<script lang="ts">
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import { unreadCountByChannel } from '../chat/messages.store';
  import type { Channel } from '../../types/gateway';

  function selectChannel(channel: Channel): void {
    activeChannel.set(channel);
  }
</script>

<nav
  class="flex w-[260px] shrink-0 flex-col border-r border-slate-800 bg-app-900"
  aria-label="Channels"
>
  {#if $activeServer}
    <header
      class="flex h-12 items-center border-b border-slate-800 px-3.5 text-sm font-bold text-white"
    >
      {$activeServer.name}
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
          <span aria-hidden="true" class="text-slate-500">#</span>
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
