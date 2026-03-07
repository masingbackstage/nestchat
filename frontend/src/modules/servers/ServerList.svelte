<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Settings } from 'lucide-svelte';
  import { servers } from '../../lib/stores/servers';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import type { Server } from '../../types/gateway';

  const dispatch = createEventDispatcher<{ openSettings: undefined }>();

  function selectServer(server: Server): void {
    activeServer.set(server);
    activeChannel.set(server.channels?.[0] ?? null);
  }
</script>

<aside
  class="flex w-[72px] shrink-0 flex-col items-center border-r border-slate-800 bg-app-950 px-2.5 py-3"
  aria-label="Servers"
>
  <div class="flex min-h-0 w-full flex-1 flex-col items-center gap-2 overflow-auto">
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
  </div>

  <button
    type="button"
    title="Ustawienia"
    aria-label="Ustawienia"
    class="mt-3 flex h-12 w-12 items-center justify-center rounded-3xl border border-slate-700 bg-slate-800 text-slate-300 transition hover:rounded-2xl hover:border-slate-500 hover:bg-slate-700 hover:text-slate-100"
    on:click={() => dispatch('openSettings')}
  >
    <Settings class="h-5 w-5" aria-hidden="true" />
  </button>
</aside>
