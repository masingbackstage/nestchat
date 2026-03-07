<script lang="ts">
  import { servers } from '../../lib/stores/servers';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import type { Server } from '../../types/gateway';

  function selectServer(server: Server): void {
    activeServer.set(server);
    activeChannel.set(server.channels?.[0] ?? null);
  }
</script>

<aside
  class="flex w-[72px] shrink-0 flex-col items-center gap-2 border-r border-slate-800 bg-app-950 px-2.5 py-3"
  aria-label="Servers"
>
  {#each $servers as server}
    <button
      type="button"
      title={server.name}
      aria-label={server.name}
      class={`h-12 w-12 border-0 text-sm font-semibold transition-all duration-150 ${
        $activeServer?.uuid === server.uuid
          ? 'rounded-2xl bg-indigo-500 text-white'
          : 'rounded-3xl bg-slate-700 text-slate-300 hover:rounded-2xl hover:bg-indigo-600 hover:text-white'
      }`}
      on:click={() => selectServer(server)}
    >
      {server.name.slice(0, 2).toUpperCase()}
    </button>
  {/each}
</aside>
