<script lang="ts">
  import { fade, scale } from 'svelte/transition';

  export let isSubmitting = false;
  export let onCancel: () => void;
  export let onConfirm: () => void;
  export let onOverlayClick: (event: MouseEvent) => void;
</script>

<div
  class="delete-message-modal-overlay"
  role="presentation"
  on:click={onOverlayClick}
  in:fade={{ duration: 130 }}
  out:fade={{ duration: 120 }}
>
  <div
    class="delete-message-modal glass-panel-strong"
    role="dialog"
    aria-modal="true"
    aria-labelledby="delete-message-title"
    tabindex="-1"
    in:scale={{ duration: 170, start: 0.96 }}
    out:scale={{ duration: 120, start: 1 }}
  >
    <h3 id="delete-message-title" class="delete-message-modal-title">Delete this message?</h3>
    <p class="delete-message-modal-copy">This action cannot be undone.</p>
    <div class="delete-message-modal-actions">
      <button
        type="button"
        class="delete-message-modal-button delete-message-modal-button-secondary"
        on:click={onCancel}
        disabled={isSubmitting}
      >
        Cancel
      </button>
      <button
        type="button"
        class="delete-message-modal-button delete-message-modal-button-danger"
        on:click={onConfirm}
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Deleting...' : 'Delete'}
      </button>
    </div>
  </div>
</div>

<style>
  .delete-message-modal-overlay {
    @apply fixed inset-0 z-[70] flex items-center justify-center bg-surface-950/75 p-4 backdrop-blur-sm;
  }

  .delete-message-modal {
    @apply w-full max-w-sm rounded-2xl p-4;
  }

  .delete-message-modal-title {
    @apply text-base font-semibold text-slate-100;
  }

  .delete-message-modal-copy {
    @apply mt-2 text-sm text-muted-200;
  }

  .delete-message-modal-actions {
    @apply mt-4 flex items-center justify-end gap-2;
  }

  .delete-message-modal-button {
    @apply rounded-xl px-3 py-1.5 text-sm transition disabled:opacity-60;
  }

  .delete-message-modal-button-secondary {
    @apply border border-white/15 text-muted-200 hover:border-glass-highlight;
  }

  .delete-message-modal-button-danger {
    @apply bg-red-600 font-medium text-white hover:bg-red-500;
  }
</style>
