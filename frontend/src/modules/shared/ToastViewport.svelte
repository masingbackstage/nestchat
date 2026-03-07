<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { removeToast, toasts } from '../../lib/stores/toast';
</script>

<div class="pointer-events-none fixed right-4 top-4 z-[90] flex w-full max-w-sm flex-col gap-2">
  {#each $toasts as toast (toast.id)}
    <div
      class={`glass-panel-strong pointer-events-auto rounded-xl px-3 py-2 ${
        toast.type === 'success'
          ? 'border-emerald-500/45 bg-emerald-500/15 text-emerald-100'
          : 'border-red-500/45 bg-red-500/15 text-red-100'
      }`}
      in:fly={{ x: 20, y: -8, duration: 180 }}
      out:fade={{ duration: 140 }}
      role="status"
      aria-live="polite"
    >
      <div class="flex items-start justify-between gap-3">
        <p class="text-sm">{toast.message}</p>
        <button
          type="button"
          class="rounded border border-white/20 px-1.5 py-0.5 text-[10px] text-muted-100 transition hover:border-glass-highlight"
          on:click={() => removeToast(toast.id)}
          aria-label="Zamknij powiadomienie"
        >
          X
        </button>
      </div>
    </div>
  {/each}
</div>
