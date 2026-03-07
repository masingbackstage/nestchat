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
  class="fixed inset-0 z-[80] flex items-center justify-center bg-surface-950/80 px-4 backdrop-blur-sm"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="glass-panel-strong w-full max-w-md rounded-[1.1rem] p-5"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-100">Account settings</h2>
      <button
        type="button"
        class="rounded-lg border border-white/15 px-2 py-1 text-xs text-muted-200 transition hover:border-glass-highlight hover:text-slate-100"
        on:click={requestClose}
        disabled={isSubmitting}
      >
        Close
      </button>
    </div>

    <p class="mb-5 text-sm text-muted-200">Manage your active account sessions.</p>

    <div class="space-y-3">
      <button
        type="button"
        class="w-full rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-glass-highlight disabled:cursor-not-allowed disabled:opacity-60"
        on:click={() => dispatch('logoutCurrent')}
        disabled={isSubmitting}
      >
        Log out of this device
      </button>

      <button
        type="button"
        class="w-full rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
        on:click={handleLogoutAllClick}
        disabled={isSubmitting}
      >
        {isConfirmingLogoutAll ? 'Confirm log out everywhere' : 'Log out of all devices'}
      </button>

      {#if isConfirmingLogoutAll}
        <button
          type="button"
          class="w-full rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-muted-200 transition hover:border-glass-highlight disabled:cursor-not-allowed disabled:opacity-60"
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
