<script lang="ts">
  import { Bell, Hash, Pin, Search, Users } from 'lucide-svelte';

  export let channelName: string | null = null;
</script>

<header class="chat-header">
  {#if channelName}
    <Hash class="h-5 w-5 text-muted-400" aria-hidden="true" />
    <h2 class="chat-header-title">{channelName}</h2>
  {:else}
    <h2 class="chat-header-title">Select a channel</h2>
  {/if}

  <div class="chat-header-actions">
    <button type="button" class="chat-header-icon-button" aria-label="Powiadomienia">
      <Bell class="h-4 w-4" />
    </button>
    <button type="button" class="chat-header-icon-button" aria-label="Pinned">
      <Pin class="h-4 w-4" />
    </button>
    <button type="button" class="chat-header-icon-button" aria-label="Members">
      <Users class="h-4 w-4" />
    </button>
    <div class="chat-header-search">
      <input type="text" readonly value="" placeholder="Search" class="chat-header-search-input" />
      <Search class="h-3.5 w-3.5 text-muted-400" />
    </div>
  </div>
</header>

<style>
  .chat-header {
    @apply flex h-16 items-center border-b border-white/10 px-5;
  }

  .chat-header-title {
    @apply truncate text-lg font-semibold text-slate-100;
  }

  .chat-header-actions {
    @apply ml-auto hidden items-center gap-4 text-muted-300 md:flex;
  }

  .chat-header-icon-button {
    @apply rounded p-1.5 transition hover:bg-white/10 hover:text-slate-100;
  }

  .chat-header-search {
    @apply flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5;
  }

  .chat-header-search-input {
    @apply w-24 bg-transparent text-xs text-muted-200 outline-none placeholder:text-muted-500;
  }
</style>
