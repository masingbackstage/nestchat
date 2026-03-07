<script lang="ts">
  import { activeChannel } from '../../lib/stores/ui';
  import { channelQueryStateById, chatConnectionStatus, messagesByChannel } from './messages.store';
  import MessageItem from './MessageItem.svelte';
  import MessageInput from './MessageInput.svelte';

  $: currentMessages = $activeChannel ? ($messagesByChannel[$activeChannel.uuid] ?? []) : [];
  $: currentChannelQuery = $activeChannel ? $channelQueryStateById[$activeChannel.uuid] : null;
  $: isInitialLoading = Boolean(
    $activeChannel && currentMessages.length === 0 && currentChannelQuery?.isLoading,
  );
</script>

<section class="flex min-w-0 flex-1 flex-col bg-app-850" aria-label="Chat">
  <header
    class="flex h-12 items-center gap-2 border-b border-slate-700 px-4 text-sm font-bold text-slate-100"
  >
    {#if $activeChannel}
      <span aria-hidden="true" class="text-slate-500">#</span>
      <h2 class="truncate">{$activeChannel.name}</h2>
    {:else}
      <h2>Wybierz kanał</h2>
    {/if}

    <span class="ml-auto rounded bg-slate-800 px-2 py-0.5 text-xs font-normal text-slate-400">
      WS: {$chatConnectionStatus}
    </span>
  </header>

  <div class="flex min-h-0 flex-1 flex-col">
    <div class="flex-1 space-y-1 overflow-auto p-3">
      {#if !$activeChannel}
        <p class="text-sm text-slate-400">Wybierz serwer i kanał, aby rozpocząć rozmowę.</p>
      {:else if isInitialLoading}
        <p class="text-sm text-slate-400">Ładowanie wiadomości...</p>
      {:else if currentMessages.length === 0}
        <p class="text-sm text-slate-400">Brak wiadomości na tym kanale.</p>
      {:else}
        {#each currentMessages as message (message.uuid)}
          <MessageItem {message} />
        {/each}
      {/if}

      {#if $activeChannel && currentChannelQuery?.error}
        <p class="mt-2 text-xs text-amber-300">
          Nie udało się odświeżyć wiadomości. Pokazuję ostatnią dostępną wersję.
        </p>
      {/if}
    </div>

    <MessageInput />
  </div>
</section>
