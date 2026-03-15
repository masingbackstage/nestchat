<script lang="ts">
  import { fly, fade } from 'svelte/transition';
  import { removeToast, toasts } from '../../lib/stores/toast';

  function getToastVariantClass(type: 'success' | 'error'): string {
    return type === 'success' ? 'toast-viewport-item-success' : 'toast-viewport-item-error';
  }
</script>

<div class="toast-viewport">
  {#each $toasts as toast (toast.id)}
    <div
      class={`glass-panel-strong toast-viewport-item ${getToastVariantClass(toast.type)}`}
      in:fly={{ x: 20, y: -8, duration: 180 }}
      out:fade={{ duration: 140 }}
      role="status"
      aria-live="polite"
    >
      <div class="toast-viewport-content">
        <p class="toast-viewport-message">{toast.message}</p>
        <button
          type="button"
          class="toast-viewport-close"
          on:click={() => removeToast(toast.id)}
          aria-label="Close toast"
        >
          X
        </button>
      </div>
    </div>
  {/each}
</div>

<style>
  .toast-viewport {
    @apply pointer-events-none fixed right-4 top-4 z-[90] flex w-full max-w-sm flex-col gap-2;
  }

  .toast-viewport-item {
    @apply pointer-events-auto rounded-xl px-3 py-2;
  }

  .toast-viewport-item-success {
    @apply border-emerald-500/45 bg-emerald-500/15 text-emerald-100;
  }

  .toast-viewport-item-error {
    @apply border-red-500/45 bg-red-500/15 text-red-100;
  }

  .toast-viewport-content {
    @apply flex items-start justify-between gap-3;
  }

  .toast-viewport-message {
    @apply text-sm;
  }

  .toast-viewport-close {
    @apply rounded border border-white/20 px-1.5 py-0.5 text-[10px] text-muted-100 transition hover:border-glass-highlight;
  }
</style>
