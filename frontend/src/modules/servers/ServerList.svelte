<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { MessageCircle, Settings } from 'lucide-svelte';
  import { servers } from '../../lib/stores/servers';
  import { activeServer, activeChannel } from '../../lib/stores/ui';
  import type { Server } from '../../types/gateway';

  const dispatch = createEventDispatcher<{ openSettings: undefined }>();

  function selectServer(server: Server): void {
    activeServer.set(server);
    activeChannel.set(server.channels?.[0] ?? null);
  }

  function selectDirectMessages(): void {
    activeServer.set(null);
    activeChannel.set(null);
  }
</script>

<aside
  class="glass-panel glass-panel-strong flex w-[78px] shrink-0 flex-col items-center rounded-panel px-2.5 py-3"
  aria-label="Servers"
>
  <button
    type="button"
    title="Direct Messages"
    aria-label="Direct Messages"
    class={`mb-2 flex h-12 w-12 items-center justify-center border-0 leading-none transition-all duration-200 ${
      !$activeServer
        ? 'rounded-2xl bg-accent-500 text-white shadow-glow'
        : 'rounded-3xl bg-surface-800 text-muted-200 hover:rounded-2xl hover:bg-surface-850 hover:text-white'
    }`}
    on:click={selectDirectMessages}
  >
    <MessageCircle class="h-5 w-5 shrink-0" aria-hidden="true" />
  </button>

  <div class="mb-2 h-px w-8 rounded-full bg-white/15"></div>

  <div class="app-scrollbar flex min-h-0 w-full flex-1 flex-col items-center gap-2 overflow-auto">
    {#each $servers as server}
      <button
        type="button"
        title={server.name}
        aria-label={server.name}
        class={`group relative h-12 w-12 border-0 text-sm font-semibold transition-all duration-200 ${
          $activeServer?.uuid === server.uuid
            ? 'rounded-2xl bg-accent-500 text-white'
            : 'rounded-3xl bg-surface-800 text-muted-200 hover:rounded-2xl hover:bg-surface-850 hover:text-white'
        }`}
        on:click={() => selectServer(server)}
      >
        <span
          class={`absolute -left-2 top-1/2 h-2 w-1 -translate-y-1/2 rounded-r-full bg-white transition-all ${
            $activeServer?.uuid === server.uuid ? 'opacity-100' : 'opacity-0 group-hover:h-4 group-hover:opacity-80'
          }`}
        ></span>
        {server.name.slice(0, 2).toUpperCase()}
      </button>
    {/each}
  </div>

  <button
    type="button"
    title="Settings"
    aria-label="Settings"
    class="mt-2 flex h-12 w-12 items-center justify-center rounded-3xl border border-white/10 bg-surface-800 text-muted-200 transition hover:rounded-2xl hover:border-glass-highlight hover:bg-surface-850 hover:text-slate-100"
    on:click={() => dispatch('openSettings')}
  >
    <Settings class="h-5 w-5" aria-hidden="true" />
  </button>
</aside>
