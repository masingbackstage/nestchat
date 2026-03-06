<script lang="ts">
  import { activeChannel } from '../../lib/stores/ui';
</script>

<section class="flex min-w-0 flex-1 flex-col bg-app-850" aria-label="Chat">
  <header class="flex h-12 items-center gap-2 border-b border-slate-700 px-4 text-sm font-bold text-slate-100">
    {#if $activeChannel}
      <span aria-hidden="true" class="text-slate-500">#</span>
      <h2 class="truncate">{$activeChannel.name}</h2>
    {:else}
      <h2>Wybierz kanał</h2>
    {/if}
  </header>

  <div class="p-4 text-sm text-slate-400">
    {#if $activeChannel}
      Wiadomości dla kanału <strong class="text-slate-200">#{$activeChannel.name}</strong> pojawią się tutaj.
    {:else}
      Wybierz serwer i kanał, aby rozpocząć rozmowę.
    {/if}
  </div>
</section>
