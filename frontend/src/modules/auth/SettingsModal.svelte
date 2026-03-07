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
  class="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/70 px-4"
  role="presentation"
  on:pointerdown={handleOverlayPointerDown}
  in:fade={{ duration: 150 }}
  out:fade={{ duration: 130 }}
>
  <div
    class="w-full max-w-md rounded-lg border border-slate-700 bg-app-900 p-5 shadow-2xl"
    role="dialog"
    aria-modal="true"
    in:scale={{ duration: 180, start: 0.96 }}
    out:scale={{ duration: 140, start: 1 }}
  >
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold text-slate-100">Ustawienia konta</h2>
      <button
        type="button"
        class="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 transition hover:border-slate-500 hover:text-slate-100"
        on:click={requestClose}
        disabled={isSubmitting}
      >
        Zamknij
      </button>
    </div>

    <p class="mb-5 text-sm text-slate-400">Zarządzaj aktywnymi sesjami konta.</p>

    <div class="space-y-3">
      <button
        type="button"
        class="w-full rounded border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-100 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
        on:click={() => dispatch('logoutCurrent')}
        disabled={isSubmitting}
      >
        Wyloguj z tego urządzenia
      </button>

      <button
        type="button"
        class="w-full rounded border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm font-medium text-red-200 transition hover:border-red-400 disabled:cursor-not-allowed disabled:opacity-60"
        on:click={handleLogoutAllClick}
        disabled={isSubmitting}
      >
        {isConfirmingLogoutAll ? 'Potwierdź wylogowanie wszystkich' : 'Wyloguj ze wszystkich urządzeń'}
      </button>

      {#if isConfirmingLogoutAll}
        <button
          type="button"
          class="w-full rounded border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-60"
          on:click={() => {
            isConfirmingLogoutAll = false;
          }}
          disabled={isSubmitting}
        >
          Anuluj
        </button>
      {/if}
    </div>
  </div>
</div>
