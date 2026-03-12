<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { MessageCircle, Settings } from 'lucide-svelte';
  import { servers } from '../../../lib/stores/servers';
  import { activeChannel, activeDMConversation, activeServer } from '../../../lib/stores/ui';
  import type { Server } from '../../../types/gateway';

  const dispatch = createEventDispatcher<{ openSettings: undefined }>();

  function selectServer(server: Server): void {
    activeServer.set(server);
    activeChannel.set(server.channels?.[0] ?? null);
    activeDMConversation.set(null);
  }

  function selectDirectMessages(): void {
    activeServer.set(null);
    activeChannel.set(null);
    activeDMConversation.set(null);
  }
</script>

<aside class="server-list glass-panel glass-panel-strong" aria-label="Servers">
  <button
    type="button"
    title="Direct Messages"
    aria-label="Direct Messages"
    class:server-list-button-active={!$activeServer}
    class:server-list-button-inactive={$activeServer}
    class="server-list-button server-list-dm-button"
    on:click={selectDirectMessages}
  >
    <MessageCircle class="server-list-icon" aria-hidden="true" />
  </button>

  <div class="server-list-divider"></div>

  <div class="server-list-items app-scrollbar">
    {#each $servers as server}
      <button
        type="button"
        title={server.name}
        aria-label={server.name}
        class:server-list-button-active={$activeServer?.uuid === server.uuid}
        class:server-list-button-inactive={$activeServer?.uuid !== server.uuid}
        class="group server-list-button server-list-server-button"
        on:click={() => selectServer(server)}
      >
        <span
          class:server-list-indicator-active={$activeServer?.uuid === server.uuid}
          class="server-list-indicator"
        ></span>
        {#if server.avatarUrl ?? server.avatar_url}
          <img
            src={server.avatarUrl ?? server.avatar_url}
            alt={server.name}
            class="server-list-avatar"
          />
        {:else}
          {server.name.slice(0, 2).toUpperCase()}
        {/if}
      </button>
    {/each}
  </div>

  <button
    type="button"
    title="Settings"
    aria-label="Settings"
    class="server-list-button server-list-settings-button"
    on:click={() => dispatch('openSettings')}
  >
    <Settings class="server-list-icon" aria-hidden="true" />
  </button>
</aside>

<style>
  .server-list {
    @apply flex w-[78px] shrink-0 flex-col items-center rounded-panel px-2.5 py-3;
  }

  .server-list-button {
    @apply flex h-12 w-12 items-center justify-center border-0 text-sm font-semibold leading-none transition-all duration-200;
  }

  .server-list-button-active {
    @apply rounded-2xl bg-accent-500 text-white shadow-glow;
  }

  .server-list-button-inactive {
    @apply rounded-3xl bg-surface-800 text-muted-200 hover:rounded-2xl hover:bg-surface-850 hover:text-white;
  }

  .server-list-dm-button {
    @apply mb-2;
  }

  .server-list-divider {
    @apply mb-2 h-px w-8 rounded-full bg-white/15;
  }

  .server-list-items {
    @apply flex min-h-0 w-full flex-1 flex-col items-center gap-2 overflow-auto;
  }

  .server-list-server-button {
    @apply relative;
  }

  .server-list-indicator {
    @apply absolute -left-2 top-1/2 h-2 w-1 -translate-y-1/2 rounded-r-full bg-white opacity-0 transition-all group-hover:h-4 group-hover:opacity-80;
  }

  .server-list-indicator-active {
    @apply h-2 opacity-100;
  }

  .server-list-avatar {
    @apply h-12 w-12 rounded-[inherit] object-cover;
  }

  .server-list-settings-button {
    @apply mt-2 rounded-3xl border border-white/10 bg-surface-800 text-muted-200 hover:rounded-2xl hover:border-glass-highlight hover:bg-surface-850 hover:text-slate-100;
  }
</style>
