<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade, scale } from 'svelte/transition';

  export let isSubmitting = false;
  let isConfirmingLogoutAll = false;

  const dispatch = createEventDispatcher<{
    close: undefined;
    logoutCurrent: undefined;
    logoutAll: undefined;
  }>();

  function requestClose(): void {
    if (isSubmitting) {
      return;
    }
    dispatch('close');
  }

  function handleOverlayPointerDown(event: PointerEvent): void {
    if (event.target !== event.currentTarget) {
      return;
    }
    requestClose();
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      requestClose();
    }
  }

  function handleLogoutAllClick(): void {
    if (isSubmitting) {
      return;
    }
    if (!isConfirmingLogoutAll) {
      isConfirmingLogoutAll = true;
      return;
    }
    dispatch('logoutAll');
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<div
  class="settings-modal-overlay"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="glass-panel-strong settings-modal"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <div class="settings-modal-header">
      <h2 class="settings-modal-title">Account settings</h2>
      <button
        type="button"
        class="settings-modal-close-button"
        on:click={requestClose}
        disabled={isSubmitting}
      >
        Close
      </button>
    </div>

    <p class="settings-modal-copy">Manage your active account sessions.</p>

    <div class="settings-modal-actions">
      <button
        type="button"
        class="settings-modal-button settings-modal-button-secondary"
        on:click={() => dispatch('logoutCurrent')}
        disabled={isSubmitting}
      >
        Log out of this device
      </button>

      <button
        type="button"
        class="settings-modal-button settings-modal-button-danger"
        on:click={handleLogoutAllClick}
        disabled={isSubmitting}
      >
        {isConfirmingLogoutAll ? 'Confirm log out everywhere' : 'Log out of all devices'}
      </button>

      {#if isConfirmingLogoutAll}
        <button
          type="button"
          class="settings-modal-button settings-modal-button-muted"
          on:click={() => {
            isConfirmingLogoutAll = false;
          }}
          disabled={isSubmitting}
        >
          Cancel
        </button>
      {/if}
    </div>
  </div>
</div>

<style>
  .settings-modal-overlay {
    @apply fixed inset-0 z-[80] flex items-center justify-center bg-surface-950/80 px-4 backdrop-blur-sm;
  }

  .settings-modal {
    @apply w-full max-w-md rounded-[1.1rem] p-5;
  }

  .settings-modal-header {
    @apply mb-4 flex items-center justify-between;
  }

  .settings-modal-title {
    @apply text-lg font-semibold text-slate-100;
  }

  .settings-modal-close-button {
    @apply rounded-lg border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight hover:text-slate-100 disabled:cursor-not-allowed disabled:opacity-60;
  }

  .settings-modal-copy {
    @apply mb-5 text-sm text-muted-200;
  }

  .settings-modal-actions {
    @apply space-y-3;
  }

  .settings-modal-button {
    @apply w-full rounded-xl px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60;
  }

  .settings-modal-button-secondary {
    @apply border border-white/15 bg-white/5 text-slate-100 hover:border-glass-highlight;
  }

  .settings-modal-button-danger {
    @apply border border-red-500/40 bg-red-500/10 text-red-200 hover:border-red-400;
  }

  .settings-modal-button-muted {
    @apply border border-white/15 bg-white/5 text-muted-200 hover:border-glass-highlight;
  }
</style>
